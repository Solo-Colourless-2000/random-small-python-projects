"""Behavioral regression tests added during the detailed review."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module_for(number):
    path = next((ROOT / 'projects').glob(f'{number}_*.py'))
    spec = importlib.util.spec_from_file_location('review_' + number, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeaderRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module_for('02')

    def test_cookie_rejects_empty_samesite(self):
        data = self.mod.parse_headers('Set-Cookie: sid=x; Secure; HttpOnly; SameSite=\n')
        self.assertTrue(any('valid samesite' in row for row in self.mod.audit(data, True)))

    def test_cookie_rejects_unknown_samesite(self):
        data = self.mod.parse_headers('Set-Cookie: sid=x; Secure; HttpOnly; SameSite=perhaps\n')
        self.assertTrue(any('valid samesite' in row for row in self.mod.audit(data, True)))

    def test_cookie_none_needs_secure(self):
        data = self.mod.parse_headers('Set-Cookie: sid=x; HttpOnly; SameSite=None\n')
        self.assertTrue(any('secure with SameSite=None' in row for row in self.mod.audit(data, True)))

    def test_cookie_valid_lax_no_missing(self):
        data = self.mod.parse_headers('Set-Cookie: sid=x; Secure; HttpOnly; SameSite=Lax\n')
        self.assertTrue(any('recognized flags' in row for row in self.mod.audit(data, True)))

    def test_bad_status_line_not_silently_discarded(self):
        with self.assertRaises(ValueError):
            self.mod.parse_headers('HTTP/INVALID 200 OK\nServer: a\n')

    def test_valid_status_line_skipped(self):
        data = self.mod.parse_headers('HTTP/1.1 200 OK\nContent-Type: text/html\n')
        self.assertEqual(data['content-type'], ['text/html'])

    def test_http_control_character_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.parse_headers('Example: a\x7fb\n')

    def test_duplicate_nosniff_requires_review(self):
        data = self.mod.parse_headers('X-Content-Type-Options: nosniff\nX-Content-Type-Options: nosniff\n')
        self.assertTrue(any('exactly one nosniff' in row for row in self.mod.audit(data, True)))

    def test_hsts_zero_age_not_positive(self):
        data = self.mod.parse_headers('Strict-Transport-Security: max-age=0\n')
        self.assertTrue(any('positive integer' in row for row in self.mod.audit(data, True)))

    def test_hsts_positive_age_only_preliminary(self):
        data = self.mod.parse_headers('Strict-Transport-Security: max-age=31536000; includeSubDomains\n')
        self.assertTrue(any('other directives need review' in row for row in self.mod.audit(data, True)))


class MatchRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module_for('04')

    def test_ioc_one_trailing_dot_supported(self):
        self.assertEqual(self.mod.normalize('domain', 'EXAMPLE.TEST.'), 'example.test')

    def test_ioc_multiple_dots_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.normalize('domain', 'example.test....')

    def test_missing_event_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'events.csv'
            file.write_text('timestamp,ip,domain,sha256\n,192.0.2.1,,\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.mod.load_csv(file, ('timestamp', 'ip', 'domain', 'sha256'))

    def test_missing_ioc_value_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / 'ioc.csv'
            file.write_text('type,value\nip,\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.mod.load_csv(file, ('type', 'value'))


class IntegrityRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module_for('05')

    def test_direct_hash_rejects_symlink_linux(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'good.txt'
            path.write_bytes(b'a')
            link = root / 'shortcut.txt'
            link.symlink_to(path)
            if not hasattr(__import__('os'), 'O_NOFOLLOW'):
                self.skipTest('Platform does not expose O_NOFOLLOW.')
            with self.assertRaises(OSError):
                self.mod.digest_file(link)

    def test_sha256_has_64_hex_digits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / 'a.txt'
            file.write_bytes(b'hello')
            self.assertEqual(len(self.mod.digest_file(file)), 64)

    def test_nonregular_and_size_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            big = root / 'big.bin'
            big.write_bytes(b'0' * (self.mod.MAX_SIZE + 1))
            with self.assertRaises(ValueError):
                self.mod.digest_file(big)


class EmailRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module_for('06')

    def test_empty_mail_input(self):
        with self.assertRaises(ValueError):
            self.mod.analyze_email('  \n')

    def test_multiple_from_addresses_do_not_count_as_one(self):
        result = self.mod.analyze_email('From: first@example.test, second@example.test\n')
        self.assertTrue(any('Could not parse' in row for row in result))

    def test_header_defects_reported(self):
        result = self.mod.analyze_email('From: a@example.test\nReply-To: <a@@bad>\n')
        self.assertTrue(any('syntax defect' in row for row in result))

    def test_still_recognizes_valid_display_name(self):
        self.assertEqual(self.mod.domain_from_header('Alice <alice@example.test>'), 'example.test')


class ThrottleRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module_for('07')

    def test_unlock_on_advance(self):
        model = self.mod.Throttle()
        for _ in range(3):
            model.attempt('FAIL')
        model.advance(30)
        self.assertEqual(model.lock_until, 0)
        self.assertEqual(model.fail_times, [])

    def test_time_expiry_exactly_at_sixty(self):
        model = self.mod.Throttle()
        model.attempt('FAIL')
        model.advance(60)
        self.assertEqual(model.fail_times, [])

    def test_reject_noninteger_advance(self):
        for invalid in (True, 1.5, '10', -1):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    self.mod.Throttle().advance(invalid)

    def test_zero_advance_is_allowed(self):
        model = self.mod.Throttle()
        self.assertIn('t=0s', model.advance(0))


if __name__ == '__main__':
    unittest.main()

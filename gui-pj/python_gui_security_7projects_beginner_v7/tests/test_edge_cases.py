"""Additional validation and boundary condition tests."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get(stem):
    file = next((ROOT / "projects").glob(stem + "*.py"))
    spec = importlib.util.spec_from_file_location(stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EdgeCases(unittest.TestCase):
    def test_auth_csv_duplicate_header(self):
        obj = get('01')
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'dup.csv'
            f.write_text('timestamp,username,ip,status,status\n1,a,192.0.2.1,FAIL,FAIL\n')
            with self.assertRaises(ValueError):
                obj.read_events(f)

    def test_auth_csv_extra_row(self):
        obj = get('01')
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'large.csv'
            f.write_text('timestamp,username,ip,status\n' + 't,a,192.0.2.1,FAIL\n' * 1001)
            with self.assertRaises(ValueError):
                obj.read_events(f)

    def test_header_casefold_and_bad_unicode_name(self):
        obj = get('02')
        headers = obj.parse_headers('Content-Security-Policy: default-src \'none\'\n')
        self.assertIn('content-security-policy', headers)
        with self.assertRaises(ValueError):
            obj.parse_headers('ヘッダー: value')

    def test_header_input_size(self):
        obj = get('02')
        with self.assertRaises(ValueError):
            obj.parse_headers('x' * (obj.MAX_TEXT + 1))

    def test_firewall_duplicate_header(self):
        obj = get('03')
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'dup.csv'
            f.write_text('protocol,port,source,action,action\nTCP,22,0.0.0.0/0,ALLOW,ALLOW\n')
            with self.assertRaises(ValueError):
                obj.read_rules(f)

    def test_firewall_ipv6_open(self):
        obj = get('03')
        self.assertTrue(obj.assess(dict(protocol='TCP', port='22',source='::/0',action='ALLOW')).startswith('REVIEW'))
        self.assertEqual(obj.assess(dict(protocol='TCP',port='22',source='::/0',action='DENY')), 'DENY rule')

    def test_ioc_unicode_and_oversized_labels(self):
        obj = get('04')
        with self.assertRaises(ValueError):
            obj.normalize('domain', '会社.example')
        with self.assertRaises(ValueError):
            obj.normalize('domain', 'a' * 64 + '.test')
        self.assertEqual(obj.normalize('ip','2001:0db8::1'),'2001:db8::1')

    def test_ioc_duplicate_header(self):
        obj = get('04')
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'dup.csv'
            f.write_text('type,value,value\nip,1.2.3.4,1.2.3.4\n')
            with self.assertRaises(ValueError):
                obj.load_csv(f, ('type','value'))

    def test_integrity_empty_dir(self):
        obj = get('05')
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(obj.snapshot(tmp), {})
            self.assertEqual(obj.compare({}, {}), [])

    def test_email_duplicate_from(self):
        obj = get('06')
        clues = obj.analyze_email('From: a@example.test\nFrom: b@example.test\n\n')
        self.assertTrue(any('exactly one' in text for text in clues))
        with self.assertRaises(ValueError):
            obj.analyze_email('a' * (obj.MAX_INPUT+1))

    def test_throttle_unlock_new_failure(self):
        obj = get('07')
        model = obj.Throttle()
        for _ in range(3):
            model.attempt('FAIL')
        model.advance(30)
        self.assertIn('1 of 3', model.attempt('FAIL'))
        self.assertEqual(model.lock_until, 0)


if __name__ == '__main__':
    unittest.main()

"""Targeted tests for tricky cases found in the additional audit."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(number):
    filename = next((ROOT / 'projects').glob(number + '_*.py'))
    spec = importlib.util.spec_from_file_location('extra_' + number, filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class AdditionalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = load('02')
        cls.firewall = load('03')
        cls.email = load('06')
        cls.throttle = load('07')

    def headers(self, text):
        return self.http.audit(self.http.parse_headers(text), True)

    def test_hsts_conflicting_directives_same_field(self):
        result = self.headers('Strict-Transport-Security: max-age=0; max-age=31536000\n')
        self.assertTrue(any('CHECK: HSTS' in line for line in result))
        self.assertFalse(any('SEEN: HSTS' in line for line in result))

    def test_hsts_two_header_fields_are_ambiguous(self):
        result = self.headers('Strict-Transport-Security: max-age=100\nStrict-Transport-Security: max-age=100\n')
        self.assertTrue(any('Multiple HSTS' in line for line in result))

    def test_hsts_no_max_age(self):
        result = self.headers('Strict-Transport-Security: includeSubDomains\n')
        self.assertTrue(any('CHECK: HSTS' in line for line in result))

    def test_hsts_non_numeric_age(self):
        result = self.headers('Strict-Transport-Security: max-age=+100\n')
        self.assertTrue(any('CHECK: HSTS' in line for line in result))

    def test_hsts_one_positive_age_preliminary(self):
        result = self.headers('Strict-Transport-Security: max-age=31536000; includeSubDomains\n')
        self.assertTrue(any('SEEN: HSTS' in line for line in result))

    def test_hsts_https_switch(self):
        data = self.http.parse_headers('Strict-Transport-Security: max-age=123\n')
        self.assertTrue(any('assessment skipped' in line for line in self.http.audit(data, False)))

    def test_cookie_invalid_name_is_not_seen(self):
        result = self.headers('Set-Cookie: =value; Secure; HttpOnly; SameSite=Lax\n')
        self.assertTrue(any('valid cookie name/value syntax' in line for line in result))

    def test_cookie_missing_equal_not_seen(self):
        result = self.headers('Set-Cookie: cookie; Secure; HttpOnly; SameSite=Lax\n')
        self.assertTrue(any('valid cookie name/value syntax' in line for line in result))

    def test_cookie_valid_name_is_seen(self):
        result = self.headers('Set-Cookie: sid=x; Secure; HttpOnly; SameSite=Lax\n')
        self.assertTrue(any('SEEN: Cookie sid' in line for line in result))

    def test_firewall_rejects_non_ascii_numeric(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'rules.csv'
            for port in ('²', '٣', '0', '65536', '-1', '', '22.0'):
                with self.subTest(port=port):
                    path.write_text('protocol,port,source,action\nTCP,'+port+',0.0.0.0/0,ALLOW\n',encoding='utf-8')
                    with self.assertRaises(ValueError):
                        self.firewall.read_rules(path)

    def test_firewall_accepts_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'rules.csv'
            path.write_text('protocol,port,source,action\nTCP,1,0.0.0.0/0,ALLOW\nTCP,65535,::/0,ALLOW\n',encoding='utf-8')
            self.assertEqual(len(self.firewall.read_rules(path)),2)

    def test_email_duplicate_reply_to_no_spurious_seen(self):
        result = self.email.analyze_email('From: a@example.test\nReply-To: b@example.test\nReply-To: a@example.test\n')
        self.assertTrue(any('Multiple Reply-To' in item for item in result))
        self.assertFalse(any('Reply-To uses the same' in item or 'differs from' in item for item in result))

    def test_email_single_reply_to_still_compared(self):
        result = self.email.analyze_email('From: a@example.test\nReply-To: b@other.example.test\n')
        self.assertTrue(any('differs from' in item for item in result))

    def test_throttle_boundary_and_virtual_clock(self):
        model = self.throttle.Throttle()
        for _ in range(3): model.attempt('FAIL')
        self.assertEqual(model.lock_until,30)
        self.assertIn('BLOCKED',model.attempt('SUCCESS'))
        model.advance(30)
        self.assertEqual(model.lock_until,0)
        self.assertEqual(model.fail_times,[])
        self.assertIn('Allowed',model.attempt('SUCCESS'))

    def test_sample_fixtures_match_manual(self):
        auth = load('01')
        visible, failed = auth.summarize(auth.read_events(ROOT/'samples/auth_events.csv'))
        self.assertEqual(len(visible),6)
        self.assertEqual(failed['198.51.100.8'],3)
        ioc = load('04')
        rows = ioc.correlate(ioc.load_csv(ROOT/'samples/indicators.csv',('type','value')),
            ioc.load_csv(ROOT/'samples/ioc_events.csv',('timestamp','ip','domain','sha256')))
        self.assertEqual(len(rows),3)

if __name__ == '__main__':
    unittest.main()

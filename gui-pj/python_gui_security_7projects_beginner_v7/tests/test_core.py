"""Run with: python3 -m unittest discover -s tests -v"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "projects"
SAMPLES = ROOT / "samples"


def module(number, filename):
    spec = importlib.util.spec_from_file_location(f"project_{number}", PROJECTS / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


P1 = module(1, "01_auth_log_board.py")
P2 = module(2, "02_http_header_audit.py")
P3 = module(3, "03_firewall_rule_viewer.py")
P4 = module(4, "04_ioc_match_console.py")
P5 = module(5, "05_integrity_baseline.py")
P6 = module(6, "06_email_header_clues.py")
P7 = module(7, "07_login_throttle_lab.py")


class AuthenticationBoardTests(unittest.TestCase):
    def test_flag_is_based_on_complete_dataset(self):
        events = P1.read_events(SAMPLES / "auth_events.csv")
        visible, counts = P1.summarize(events, "bob")
        self.assertEqual(len(visible), 2)
        self.assertEqual(counts["198.51.100.8"], 3)

    def test_bad_row_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.csv"
            path.write_text("timestamp,username,ip,status\nx,a,invalid,FAIL\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                P1.read_events(path)


class HeadersTests(unittest.TestCase):
    def test_duplicate_cookie_headers_preserved(self):
        data = P2.parse_headers("HTTP/1.1 200 OK\nSet-Cookie: a=1\nSet-Cookie: b=2\n")
        self.assertEqual(len(data["set-cookie"]), 2)
        self.assertEqual(sum("Cookie" in x for x in P2.audit(data, True)), 2)

    def test_invalid_header_and_hsts_scope(self):
        with self.assertRaises(ValueError):
            P2.parse_headers(" invalid: x")
        result = P2.audit({}, False)
        self.assertTrue(any("skipped" in item for item in result))


class FirewallTests(unittest.TestCase):
    def test_source_scope(self):
        rules = P3.read_rules(SAMPLES / "firewall_rules.csv")
        self.assertEqual(len(rules), 5)
        self.assertTrue(P3.assess(rules[0]).startswith("REVIEW"))
        self.assertFalse(P3.assess(rules[2]).startswith("REVIEW"))
        self.assertEqual(P3.assess(rules[3]), "DENY rule")
        self.assertTrue(P3.assess(rules[4]).startswith("REVIEW"))

    def test_invalid_port(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.csv"
            path.write_text("protocol,port,source,action\nTCP,65536,0.0.0.0/0,ALLOW\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                P3.read_rules(path)


class IndicatorTests(unittest.TestCase):
    def test_correlation(self):
        a = P4.load_csv(SAMPLES / "indicators.csv", ("type", "value"))
        b = P4.load_csv(SAMPLES / "ioc_events.csv", ("timestamp",) + P4.TYPES)
        self.assertEqual(len(P4.correlate(a, b)), 3)

    def test_validation(self):
        self.assertEqual(P4.normalize("domain", "EXAMPLE.TEST."), "example.test")
        with self.assertRaises(ValueError):
            P4.normalize("sha256", "broken")
        with self.assertRaises(ValueError):
            P4.normalize("domain", "-bad.example.test")


class IntegrityTests(unittest.TestCase):
    def test_change_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "a.txt").write_text("before", encoding="utf-8")
            (folder / "b.txt").write_text("delete me", encoding="utf-8")
            first = P5.snapshot(folder)
            (folder / "a.txt").write_text("after", encoding="utf-8")
            (folder / "b.txt").unlink()
            (folder / "c.txt").write_text("add me", encoding="utf-8")
            outcomes = dict(P5.compare(first, P5.snapshot(folder)))
            self.assertEqual(outcomes, {"a.txt": "MODIFIED", "b.txt": "REMOVED", "c.txt": "ADDED"})

    def test_symlink_ignored_and_size_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "sample.txt").write_text("a", encoding="utf-8")
            (folder / "pointer.txt").symlink_to(folder / "sample.txt")
            self.assertEqual(set(P5.snapshot(folder)), {"sample.txt"})
            (folder / "huge.bin").write_bytes(b"x" * (P5.MAX_SIZE + 1))
            with self.assertRaises(ValueError):
                P5.snapshot(folder)


class EmailTests(unittest.TestCase):
    def test_mismatch_does_not_claim_proof(self):
        results = P6.analyze_email((SAMPLES / "mail_headers.txt").read_text())
        self.assertTrue(any("differs" in x for x in results))
        self.assertTrue(any("not proof" in x for x in results))

    def test_no_reply_to(self):
        self.assertTrue(any("No Reply-To" in x for x in P6.analyze_email(
            "From: Test <test@example.test>\nSubject: Hello\n")))


class ThrottleTests(unittest.TestCase):
    def test_lockout_and_recovery(self):
        model = P7.Throttle()
        self.assertIn("failure", model.attempt("FAIL"))
        model.advance(10)
        model.attempt("FAIL")
        self.assertIn("LOCKED", model.attempt("FAIL"))
        self.assertIn("BLOCKED", model.attempt("SUCCESS"))
        model.advance(30)
        self.assertIn("Allowed", model.attempt("SUCCESS"))
        self.assertEqual(model.lock_until, 0)

    def test_window_expires(self):
        model = P7.Throttle()
        model.attempt("FAIL")
        model.advance(60)
        self.assertIn("1 of 3", model.attempt("FAIL"))
        with self.assertRaises(ValueError):
            model.advance(-1)


if __name__ == "__main__":
    unittest.main()

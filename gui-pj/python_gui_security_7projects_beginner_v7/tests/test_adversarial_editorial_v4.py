"""Independently motivated boundary and misleading-verdict regressions for v4."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(prefix):
    path = next((ROOT / "projects").glob(prefix + "_*.py"))
    spec = importlib.util.spec_from_file_location("review_v4_" + prefix, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeaderAuditV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("02")

    def inspect(self, raw):
        return self.mod.audit(self.mod.parse_headers(raw), True)

    def test_oversized_hsts_positive_must_not_crash(self):
        result = self.inspect("Strict-Transport-Security: max-age=" + "9" * 5000)
        self.assertTrue(any(x.startswith("SEEN: HSTS") for x in result))

    def test_oversized_hsts_zero_is_not_positive(self):
        result = self.inspect("Strict-Transport-Security: max-age=" + "0" * 5000)
        self.assertTrue(any(x.startswith("CHECK: HSTS") for x in result))

    def test_hsts_ambiguous_duplicate_is_check(self):
        result = self.inspect("Strict-Transport-Security: max-age=5; max-age=6")
        self.assertTrue(any(x.startswith("CHECK: HSTS") for x in result))

    def test_blank_headers_rejected_as_input(self):
        for raw in ("", "\n\r\n", "HTTP/1.1 200 OK\n"):
            with self.subTest(raw=repr(raw)), self.assertRaises(ValueError):
                self.mod.parse_headers(raw)

    def test_regular_sample_still_classified(self):
        raw = (ROOT / "samples/response_headers.txt").read_text()
        result = self.inspect(raw)
        self.assertTrue(any("Cookie sid" in x and x.startswith("SEEN:") for x in result))


class FirewallV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("03")

    def csv(self, text):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "data.csv"
            file.write_text("protocol,port,source,action\n" + text, encoding="utf-8")
            return self.mod.read_rules(file)

    def test_host_bits_are_rejected_not_silently_masked(self):
        with self.assertRaisesRegex(ValueError, "host bits"):
            self.csv("TCP,22,192.0.2.17/24,ALLOW\n")

    def test_network_aligned_cidr_accepted(self):
        self.assertEqual(self.csv("TCP,22,192.0.2.0/24,ALLOW\n")[0]["source"], "192.0.2.0/24")

    def test_host_address_without_cidr_maps_to_single_host(self):
        self.assertEqual(self.csv("TCP,22,192.0.2.17,ALLOW\n")[0]["source"], "192.0.2.17/32")

    def test_oversized_decimal_port_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Port must be"):
            self.csv("TCP," + "9" * 7000 + ",0.0.0.0/0,ALLOW\n")

    def test_any_port_ipv6_global_still_reviewed(self):
        rule = self.csv("TCP,any,::/0,ALLOW\n")[0]
        self.assertIn("REVIEW", self.mod.assess(rule))


class IocV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("04")

    def test_scoped_ipv6_rejected(self):
        for ip in ("fe80::1%eth0", "fe80::1%1"):
            with self.subTest(ip=ip), self.assertRaisesRegex(ValueError, "scope identifiers"):
                self.mod.normalize("ip", ip)

    def test_plain_ipv6_remains_supported(self):
        self.assertEqual(self.mod.normalize("ip", "2001:0db8::0001"), "2001:db8::1")

    def test_trailing_dot_domain_normalization(self):
        self.assertEqual(self.mod.normalize("domain", "EXAMPLE.TEST."), "example.test")

    def test_too_long_csv_rejected_before_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "huge.csv"
            file.write_bytes(b"type,value\n" + b"X" * (self.mod.MAX_CSV_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                self.mod.load_csv(file, ("type", "value"))


class EmailV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("06")

    def test_duplicate_from_has_no_positive_comparison(self):
        lines = self.mod.analyze_email("From: a@example.test\nFrom: b@elsewhere.test\nReply-To: z@example.test\n")
        self.assertTrue(any("sender comparison skipped" in x for x in lines))
        self.assertFalse(any(x.startswith("SEEN: Reply-To") for x in lines))

    def test_missing_from_has_no_positive_comparison(self):
        lines = self.mod.analyze_email("Reply-To: z@example.test\n")
        self.assertFalse(any(x.startswith("SEEN: Reply-To") for x in lines))
        self.assertTrue(any("valid single From needed" in x for x in lines))

    def test_valid_single_from_still_compares(self):
        lines = self.mod.analyze_email("From: a@example.test\nReply-To: b@example.test\n")
        self.assertTrue(any(x.startswith("SEEN: Reply-To") for x in lines))

    def test_domain_too_long_rejected(self):
        long_domain = ".".join(["a" * 60] * 5) + ".test"
        self.assertGreater(len(long_domain), 253)
        self.assertEqual(self.mod.domain_from_header("user@" + long_domain), "")

    def test_multi_address_from_not_seen(self):
        lines = self.mod.analyze_email("From: a@example.test, b@example.test\nReply-To: c@example.test\n")
        self.assertFalse(any(x.startswith("SEEN: Reply-To") for x in lines))


class InputBoundsV4(unittest.TestCase):
    def test_auth_csv_size_guard(self):
        mod = load("01")
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "oversize.csv"
            file.write_bytes(b"X" * (mod.MAX_CSV_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                mod.read_events(file)

    def test_firewall_csv_size_guard(self):
        mod = load("03")
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "oversize.csv"
            file.write_bytes(b"X" * (mod.MAX_CSV_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "1 MiB"):
                mod.read_rules(file)

    def test_small_csvs_still_work(self):
        a = load("01")
        f = load("03")
        self.assertEqual(len(a.read_events(ROOT / "samples/auth_events.csv")), 6)
        self.assertEqual(len(f.read_rules(ROOT / "samples/firewall_rules.csv")), 5)


if __name__ == "__main__":
    unittest.main()

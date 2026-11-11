"""Offline regression tests for the ten independent security learning tools."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PROJECTS = sorted((BASE / "projects").glob("[0-9][0-9]_*.py"))
SAMPLES = BASE / "samples"


def module(number):
    path = PROJECTS[number - 1]
    spec = importlib.util.spec_from_file_location(f"learning_p{number}", path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def cli(number, *args):
    return subprocess.run([sys.executable, str(PROJECTS[number - 1]), *map(str, args)],
                          capture_output=True, text=True, timeout=8)


class LearningTools(unittest.TestCase):
    def test_inventory(self):
        self.assertEqual(len(PROJECTS), 10)
        self.assertEqual([p.name[:2] for p in PROJECTS], [f"{i:02d}" for i in range(1, 11)])

    def test_01_main(self):
        result = cli(1, SAMPLES / "response_headers.txt", "https")
        self.assertEqual(result.returncode, 0)
        self.assertIn("PASS nosniff", result.stdout)
        self.assertIn("REVIEW HSTS", result.stdout)

    def test_01_invalid_field_token(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "bad_headers.txt"
            f.write_text("HTTP/1.1 200 OK\nBad Name: value\n", encoding="utf-8")
            self.assertEqual(cli(1, f, "http").returncode, 1)

    def test_01_http(self):
        self.assertIn("only meaningful", cli(1, SAMPLES / "response_headers.txt", "http").stdout)

    def test_01_missing(self):
        self.assertEqual(cli(1, "no-such-file", "https").returncode, 1)

    def test_01_usage(self):
        self.assertEqual(cli(1).returncode, 2)

    def test_01_duplicate(self):
        self.assertIn("duplicate", " ".join(module(1).inspect({"x": ["a", "b"]}, "http")))

    def test_01_bad_headers(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "h"
            f.write_text(" folded-header\n", encoding="utf-8")
            self.assertEqual(cli(1, f, "https").returncode, 1)

    def test_02_main(self):
        result = cli(2, SAMPLES / "cookies.txt")
        self.assertEqual(result.returncode, 0)
        self.assertIn("__Host-session: PASS", result.stdout)
        self.assertIn("tracking: REVIEW", result.stdout)

    def test_02_parse(self):
        n, v, a = module(2).parse_cookie("Set-Cookie: a=hi; Secure; SameSite=Lax")
        self.assertEqual((n, v, a["samesite"]), ("a", "hi", "Lax"))

    def test_02_prefix(self):
        self.assertIn("__Host-", " ".join(module(2).review("__Host-abc", {})))

    def test_02_unknown_samesite(self):
        self.assertTrue(any("samesite" in s for s in module(2).review("abc", {"secure": "", "httponly": "", "samesite": "unknown"})))

    def test_02_duplicate_cookie_attribute(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module(2).parse_cookie("Set-Cookie: id=abc; Secure; secure")

    def test_02_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "c"
            p.write_text("")
            self.assertEqual(cli(2, p).returncode, 1)

    def test_02_usage(self):
        self.assertEqual(cli(2).returncode, 2)

    def test_03_demo(self):
        result = cli(3, "demo")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Status: OPEN", result.stdout)
        self.assertIn("LAB SERVICE", result.stdout)

    def test_03_invalid_port(self):
        for value in ("0", "65536", "garbage", "-1", "1.5"):
            with self.subTest(value=value):
                self.assertEqual(cli(3, "check", value).returncode, 2)

    def test_03_usage(self):
        self.assertEqual(cli(3).returncode, 2)

    def test_03_target_fixed(self):
        self.assertEqual(module(3).HOST, "127.0.0.1")
        self.assertEqual(cli(3, "check", "1", "localhost").returncode, 2)

    def test_04_allowed(self):
        for mode in ("safe", "unsafe"):
            result = cli(4, mode, "public.txt")
            self.assertEqual(result.returncode, 0)
            self.assertIn("public training file", result.stdout)

    def test_04_traversal_compares_modes(self):
        for payload in ("../secret.txt", "%2e%2e%2fsecret.txt"):
            self.assertEqual(cli(4, "safe", payload).returncode, 1)
            self.assertIn("Private training sample", cli(4, "unsafe", payload).stdout)

    def test_04_unsafe_is_still_confined_to_sample_folder(self):
        self.assertEqual(cli(4, "unsafe", "../../../etc/passwd").returncode, 1)
        self.assertEqual(cli(4, "unsafe", "/etc/passwd").returncode, 1)

    def test_04_symlink_escape_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir()
            secret = Path(temp) / "secret.txt"
            secret.write_text("secret")
            (root / "link.txt").symlink_to(secret)
            with self.assertRaises(ValueError):
                module(4).choose(root, "link.txt", "safe")

    def test_04_usage(self):
        self.assertEqual(cli(4).returncode, 2)
        self.assertEqual(cli(4, "safe").returncode, 2)

    def test_05_unsafe(self):
        self.assertEqual(module(5).find_accounts("unsafe", "' OR 1=1 --"), ["alice", "bob"])

    def test_05_safe(self):
        self.assertEqual(module(5).find_accounts("safe", "' OR 1=1 --"), [])
        self.assertEqual(module(5).find_accounts("safe", "bob"), ["bob"])

    def test_05_cli(self):
        self.assertIn("Matches: (none)", cli(5, "safe", "' OR 1=1 --").stdout)
        self.assertEqual(cli(5, "unsafe", "'" * 90).returncode, 2)

    def test_05_usage(self):
        self.assertEqual(cli(5).returncode, 2)

    def test_06_unprotected(self):
        result = cli(6, "unprotected")
        self.assertEqual(result.returncode, 0)
        self.assertIn("ATTEMPT carol: MATCH", result.stdout)
        self.assertIn("Attempts: 4", result.stdout)

    def test_06_protected(self):
        result = cli(6, "protected")
        self.assertEqual(result.returncode, 0)
        self.assertIn("BLOCKED carol: lab-wide attempt cap", result.stdout)
        self.assertIn("BLOCKED dave: lab-wide attempt cap", result.stdout)
        self.assertIn("Attempts: 2", result.stdout)
        self.assertIn("Matched fake accounts: alice", result.stdout)

    def test_06_function(self):
        attempts, successes = module(6).simulate("unprotected")
        self.assertEqual(attempts, 4)
        self.assertEqual(successes, ["alice", "carol"])
        protected, matched = module(6).simulate("protected")
        self.assertEqual((protected, matched), (2, ["alice"]))

    def test_06_usage(self):
        self.assertEqual(cli(6).returncode, 2)
        self.assertEqual(cli(6, "unexpected").returncode, 2)

    def test_07_roundtrip(self):
        token = module(7).create("alice", "viewer")
        self.assertEqual(module(7).verify(token), {"role": "viewer", "user": "alice"})
        self.assertIn("VALID", cli(7, "verify", token).stdout)

    def test_07_role_tamper(self):
        mod = module(7)
        original = mod.create("alice", "viewer")
        forged = mod.tamper(original, "admin")
        self.assertEqual(mod.inspect_untrusted(forged)["role"], "admin")
        self.assertEqual(cli(7, "verify", forged).returncode, 1)
        self.assertIn("UNTRUSTED", cli(7, "inspect", forged).stdout)
        self.assertIn("admin", cli(7, "inspect", forged).stdout)

    def test_07_invalid(self):
        for token in ("", "garbage", "e30.??", "a" * 600):
            with self.subTest(token=token[:12]):
                self.assertEqual(cli(7, "verify", token).returncode, 1)

    def test_07_inspect_limit(self):
        self.assertEqual(cli(7, "inspect", "a" * 520 + ".z").returncode, 1)

    def test_07_bad_role(self):
        self.assertEqual(cli(7, "create", "alice", "admin").returncode, 2)
        self.assertEqual(cli(7, "create", "", "viewer").returncode, 2)

    def test_07_usage(self):
        self.assertEqual(cli(7).returncode, 2)

    def test_08_owner(self):
        self.assertTrue(module(8).permitted("bob", "notes", "edit"))

    def test_08_idor_both_modes(self):
        self.assertTrue(module(8).check_access("unsafe", "alice", "notes", "read"))
        self.assertFalse(module(8).check_access("safe", "alice", "notes", "read"))
        self.assertIn("ALLOW", cli(8, "unsafe", "alice", "notes", "read").stdout)
        self.assertIn("DENY", cli(8, "safe", "alice", "notes", "read").stdout)

    def test_08_admin(self):
        self.assertTrue(module(8).permitted("root", "notes", "edit"))

    def test_08_unknown(self):
        self.assertFalse(module(8).permitted("nobody", "notes", "read"))
        self.assertFalse(module(8).permitted("alice", "unknown", "read"))
        self.assertFalse(module(8).check_access("unsafe", "ghost", "notes", "read"))

    def test_08_usage(self):
        self.assertEqual(cli(8).returncode, 2)
        self.assertEqual(cli(8, "safe", "alice", "notes", "delete").returncode, 2)

    def test_09_main(self):
        r = cli(9, SAMPLES / "synthetic_traffic.pcap")
        self.assertEqual(r.returncode, 0)
        self.assertIn("UDP 192.0.2.10:53000", r.stdout)
        self.assertIn("TCP 192.0.2.10:50222", r.stdout)
        self.assertIn("Records: 2", r.stdout)

    def test_09_bad_magic(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.pcap"
            p.write_bytes(b"NOT PCAP" + b"\0" * 32)
            self.assertEqual(cli(9, p).returncode, 1)

    def test_09_truncated(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.pcap"
            p.write_bytes((SAMPLES / "synthetic_traffic.pcap").read_bytes()[:-1])
            self.assertEqual(cli(9, p).returncode, 1)

    def test_09_short_frame(self):
        self.assertIn("SKIP", module(9).summarize_frame(b"tiny"))

    def test_09_short_tcp_and_udp(self):
        mod = module(9)
        ethernet = b"\x00" * 12 + b"\x08\x00"
        for protocol, body_len in ((6, 4), (17, 4)):
            ip = bytearray(20 + body_len)
            ip[0] = 0x45
            ip[2:4] = len(ip).to_bytes(2, "big")
            ip[9] = protocol
            self.assertIn("SKIP short transport header", mod.summarize_frame(ethernet + ip))

    def test_09_usage(self):
        self.assertEqual(cli(9).returncode, 2)

    def test_10_main(self):
        r = cli(10, SAMPLES / "request_ambiguous.http")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Transfer-Encoding with Content-Length", r.stdout)

    def test_10_simple(self):
        self.assertIn("No basic framing conflict", cli(10, SAMPLES / "request_simple.http").stdout)

    def test_10_dup_cl(self):
        request = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\nContent-Length: 6\r\n\r\n"
        self.assertTrue(any("duplicate" in item for item in module(10).check_request(request)))

    def test_10_lf_only(self):
        with self.assertRaises(ValueError):
            module(10).check_request(b"GET / HTTP/1.1\nHost: x\n\n")

    def test_10_folded(self):
        with self.assertRaises(ValueError):
            module(10).check_request(b"GET / HTTP/1.1\r\n x: y\r\n\r\n")

    def test_10_bad_cl(self):
        r = module(10).check_request(b"POST / HTTP/1.1\r\nContent-Length: -1\r\n\r\n")
        self.assertTrue(any("malformed" in item for item in r))

    def test_10_invalid_header_name(self):
        with self.assertRaisesRegex(ValueError, "invalid field name"):
            module(10).check_request(b"GET / HTTP/1.1\r\nHost: x\r\nBad Name: y\r\n\r\n")

    def test_10_host_required(self):
        notes = module(10).check_request(b"GET / HTTP/1.1\r\n\r\n")
        self.assertTrue(any("Host" in note for note in notes))

    def test_10_usage(self):
        self.assertEqual(cli(10).returncode, 2)


    def test_01_set_cookie_can_repeat(self):
        mod = module(1)
        notes = mod.inspect({"set-cookie": ["x=1", "y=2"]}, "https")
        self.assertFalse(any("duplicate: set-cookie" in note for note in notes))

    def test_02_invalid_cookie_name_and_value(self):
        mod = module(2)
        for line in ("Set-Cookie: bad name=x; Secure", "Set-Cookie: ok=a,b; Secure", "Set-Cookie: ok=a b; Secure"):
            with self.subTest(line=line), self.assertRaises(ValueError):
                mod.parse_cookie(line)

    def test_02_invalid_attribute_name(self):
        mod = module(2)
        for line in ("Set-Cookie: x=y; bad name=value", "Set-Cookie: x=y; bad\x7f=1"):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "invalid or duplicate"):
                mod.parse_cookie(line)

    def test_02_nonempty_secure_and_httponly_flags(self):
        mod = module(2)
        name, _, attrs = mod.parse_cookie("Set-Cookie: __Host-x=abc; Path=/; Secure=0; HttpOnly=no; SameSite=None")
        messages = " ".join(mod.review(name, attrs))
        self.assertIn("unexpected secure flag value", messages)
        self.assertIn("unexpected httponly flag value", messages)
        self.assertNotIn("requires Secure", messages)
        self.assertNotIn("__Host- needs", messages)

    def test_09_tcp_data_offset(self):
        mod = module(9)
        ethernet = b"\x00" * 12 + b"\x08\x00"
        packet = bytearray(40)
        packet[0] = 0x45
        packet[2:4] = (40).to_bytes(2, "big")
        packet[9] = 6
        packet[20+12] = 0x40   # TCP data offset 4 -> 16 bytes, below minimum 20.
        self.assertIn("SKIP invalid TCP data offset", mod.summarize_frame(ethernet + packet))
        packet[20+12] = 0x60   # Offset 6 -> 24 bytes, longer than packet.
        self.assertIn("SKIP invalid TCP data offset", mod.summarize_frame(ethernet + packet))

    def test_09_udp_declared_length(self):
        mod = module(9)
        ethernet = b"\x00" * 12 + b"\x08\x00"
        packet = bytearray(28)
        packet[0] = 0x45
        packet[2:4] = (28).to_bytes(2, "big")
        packet[9] = 17
        for value in (7, 50):
            packet[20+4:20+6] = value.to_bytes(2, "big")
            with self.subTest(value=value):
                self.assertIn("SKIP invalid UDP length", mod.summarize_frame(ethernet + packet))

    def test_09_invalid_snaplen(self):
        mod = module(9)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"test.pcap"
            data = bytearray((SAMPLES / "synthetic_traffic.pcap").read_bytes())
            data[16:20] = (1).to_bytes(4, "little")
            p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "expected PCAP"):
                mod.parse_pcap(p)

    def test_10_reject_embedded_bare_lf(self):
        mod = module(10)
        with self.assertRaisesRegex(ValueError, "bare line break"):
            mod.check_request(b"GET / HTTP/1.1\r\nHost: localhost\nX-Extra: yes\r\n\r\n")

    def test_10_reject_control_bytes(self):
        mod = module(10)
        with self.assertRaisesRegex(ValueError, "control byte"):
            mod.check_request(b"GET / HTTP/1.1\r\nHost: localhost\x00\r\n\r\n")

    def test_10_reject_empty_target(self):
        with self.assertRaisesRegex(ValueError, "request line"):
            module(10).check_request(b"GET  HTTP/1.1\r\nHost: localhost\r\n\r\n")

    def test_10_cl_body_consistency(self):
        mod = module(10)
        good = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 3\r\n\r\nabc"
        bad = good[:-1]
        self.assertEqual(mod.check_request(good), ["No basic framing conflict detected (not a full parser)"])
        self.assertTrue(any("does not match" in x for x in mod.check_request(bad)))


    def test_03_closed_check_returns_failure_not_implicit_success(self):
        from unittest.mock import patch
        mod = module(3)
        with patch.object(mod, "probe", return_value=("CLOSED/UNREACHABLE", "")):
            with patch.object(sys, "argv", ["03_loopback_probe.py", "check", "12345"]):
                self.assertEqual(mod.main(), 1)

    def test_03_open_without_expected_banner_is_still_connected(self):
        from unittest.mock import patch
        mod = module(3)
        with patch.object(mod, "probe", return_value=("OPEN", "(no banner within timeout)")):
            with patch.object(sys, "argv", ["03_loopback_probe.py", "check", "12345"]):
                self.assertEqual(mod.main(), 0)

    def test_03_open_with_non_demo_banner_is_connected(self):
        from unittest.mock import patch
        mod = module(3)
        with patch.object(mod, "probe", return_value=("OPEN", "OTHER SERVICE")):
            with patch.object(sys, "argv", ["03_loopback_probe.py", "check", "12345"]):
                self.assertEqual(mod.main(), 0)

    def test_06_limit_actually_prevents_later_match(self):
        mod = module(6)
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            unprotected = mod.simulate("unprotected")
            protected = mod.simulate("protected")
        self.assertEqual(unprotected, (4, ["alice", "carol"]))
        self.assertEqual(protected, (2, ["alice"]))

    def test_09_shorter_udp_length_than_ipv4_payload(self):
        mod = module(9)
        ether = b"\0" * 12 + b"\x08\x00"
        ip = bytearray(20 + 10)
        ip[0] = 0x45
        ip[2:4] = len(ip).to_bytes(2, "big")
        ip[9] = 17
        ip[24:26] = (8).to_bytes(2, "big")
        self.assertIn("SKIP invalid UDP length", mod.summarize_frame(ether + ip))

    def test_09_microsecond_timestamp_range(self):
        mod = module(9)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.pcap"
            source = bytearray((SAMPLES / "synthetic_traffic.pcap").read_bytes())
            source[28:32] = (1_000_000).to_bytes(4, "little")
            p.write_bytes(source)
            with self.assertRaisesRegex(ValueError, "microsecond timestamp"):
                mod.parse_pcap(p)

    def test_10_oversize_cl_yields_review_not_exception(self):
        mod = module(10)
        data = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: " + b"9" * 5000 + b"\r\n\r\n"
        notes = mod.check_request(data)
        self.assertTrue(any("oversized Content-Length" in line for line in notes))

    def test_10_target_rejects_controls_and_raw_non_ascii(self):
        mod = module(10)
        for target in (b"/bad\x00x", b"/foo\x7f", b"/caf\xc3\xa9", b"/tab\t"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "request target"):
                mod.check_request(b"GET " + target + b" HTTP/1.1\r\nHost: localhost\r\n\r\n")



    def test_01_empty_file_is_an_input_error(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "empty.txt"
            file.write_bytes(b"")
            self.assertEqual(cli(1, file, "https").returncode, 1)

    def test_01_empty_field_is_valid_but_empty_policy_is_not_a_pass(self):
        mod = module(1)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "empty_headers.txt"
            file.write_bytes(b"HTTP/1.1 200 OK\r\nContent-Security-Policy:\r\n"
                             b"Referrer-Policy: \r\nStrict-Transport-Security:\r\n\r\nbody ignored")
            fields = mod.read_headers(file)
            self.assertEqual(fields["content-security-policy"], [""])
            messages = mod.inspect(fields, "https")
            self.assertTrue(any("CSP: missing or empty" in m for m in messages))
            self.assertTrue(any("HSTS: missing or empty" in m for m in messages))
            self.assertNotIn("body", fields)

    def test_01_control_in_header_value_rejected(self):
        mod = module(1)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "bad_headers.txt"
            for text in (b"X-Name: hi\x00there\n", b"X-Name: hi\x7fthere\n"):
                file.write_bytes(text)
                with self.assertRaisesRegex(ValueError, "control character"):
                    mod.read_headers(file)

    def test_01_bare_cr_and_invalid_status_line_rejected(self):
        mod = module(1)
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "status.txt"
            for text, expected in ((b"X-Test: one\rtwo", "bare CR"),
                                   (b"HTTP/1.1 UNKNOWN\nX-Test: yes\n", "status line")):
                file.write_bytes(text)
                with self.assertRaisesRegex(ValueError, expected):
                    mod.read_headers(file)

    def test_02_unbalanced_quoted_value_rejected(self):
        mod = module(2)
        for raw in ('Set-Cookie: id="abc; Secure',
                    'Set-Cookie: id=abc"; Secure',
                    'Set-Cookie: id="; Secure'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "quotes"):
                mod.parse_cookie(raw)
        self.assertEqual(mod.parse_cookie('Set-Cookie: id="abc"; Secure')[1], '"abc"')

    def test_03_receive_error_does_not_erase_successful_connect(self):
        from unittest.mock import patch
        mod = module(3)
        class BrokenPeer:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def settimeout(self, seconds):
                pass
            def recv(self, size):
                raise ConnectionResetError("reset after handshake")
        with patch.object(mod.socket, "create_connection", return_value=BrokenPeer()):
            self.assertEqual(mod.probe(12345), ("OPEN", "(banner read failed)"))

    def test_04_encoded_traversal_remains_bounded_to_samples(self):
        mod = module(4)
        with self.assertRaises((OSError, ValueError)):
            mod.choose(mod.ROOT, "%2e%2e%2f%2e%2e%2fetc%2fpasswd", "unsafe")

    def test_07_known_training_key_allows_resigning(self):
        mod = module(7)
        import json
        payload = mod.encode(json.dumps({"role": "admin", "user": "alice"},
                                            sort_keys=True, separators=(",", ":")).encode("ascii"))
        resigned = payload + "." + mod.encode(mod.sign(payload))
        # HMAC checks authenticity relative to the key, not whether a role is authorized.
        self.assertEqual(mod.verify(resigned)["role"], "admin")

    def test_09_nonipv4_or_tiny_frame_skipped(self):
        mod = module(9)
        self.assertIn("SKIP", mod.summarize_frame(b""))
        self.assertIn("SKIP", mod.summarize_frame(b"\x00" * 12 + b"\x86\xdd" + b"\x00" * 40))

    def test_10_duplicate_host_review_not_pass(self):
        mod = module(10)
        notes = mod.check_request(b"GET / HTTP/1.1\r\nHost: first\r\nHost: second\r\n\r\n")
        self.assertTrue(any("repeated Host" in note for note in notes))





    def test_02_lone_cr_in_saved_header_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "cookies.txt"
            p.write_bytes(b"Set-Cookie: a=1; Secure\rSet-Cookie: b=2; HttpOnly\n")
            result = cli(2, p)
            self.assertEqual(result.returncode, 1)
            self.assertIn("bare CR", result.stdout)

    def test_02_normal_lf_and_crlf_remain_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "cookies.txt"
            p.write_bytes(b"Set-Cookie: a=1; Secure; HttpOnly; SameSite=Lax\r\nSet-Cookie: b=2; Secure; HttpOnly; SameSite=Lax\n")
            result = cli(2, p)
            self.assertEqual(result.returncode, 0)
            self.assertIn("a: PASS", result.stdout)
            self.assertIn("b: PASS", result.stdout)

    def test_03_port_input_length_bounded(self):
        r = cli(3, "check", "1" * 20000)
        self.assertEqual(r.returncode, 2)
        self.assertIn("port", r.stdout)

    def test_07_reject_padded_signature(self):
        mod = module(7)
        token = mod.create("alice", "viewer")
        self.assertEqual(cli(7, "verify", token).returncode, 0)
        self.assertEqual(cli(7, "verify", token + "=").returncode, 1)

    def test_07_reject_noncanonical_base64url(self):
        mod = module(7)
        self.assertEqual(mod.decode("e30"), b"{}")
        with self.assertRaisesRegex(ValueError, "non-canonical"):
            mod.decode("e31")

    def test_07_reject_base64_standard_alphabet(self):
        mod = module(7)
        with self.assertRaises(ValueError):
            mod.decode("+/8")

    def test_07_roundtrip_multiple_payload_lengths(self):
        mod = module(7)
        for text in (b"a", b"ab", b"abc", b"abcd", b"abcdefg"):
            with self.subTest(text=text):
                self.assertEqual(mod.decode(mod.encode(text)), text)

    def test_10_unframed_extra_bytes_are_reviewed(self):
        req = b"POST / HTTP/1.1\r\nHost: localhost\r\n\r\nDATA"
        self.assertTrue(any("extra bytes without" in note for note in module(10).check_request(req)))

    def test_10_transfer_encoding_is_not_silently_passed(self):
        for payload in (b"not-chunked", b"0\r\n\r\n"):
            request = b"POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n" + payload
            notes = module(10).check_request(request)
            self.assertTrue(any("not decoded or validated" in n for n in notes))
            self.assertNotIn("No basic framing conflict detected (not a full parser)", notes)

    def test_10_valid_content_length_still_clean(self):
        req = b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\nDATA"
        self.assertEqual(module(10).check_request(req), ["No basic framing conflict detected (not a full parser)"])

    def test_10_no_body_or_length_remains_clean(self):
        req = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        self.assertEqual(module(10).check_request(req), ["No basic framing conflict detected (not a full parser)"])

    def test_10_transfer_encoding_with_cl_always_reviews(self):
        request = b"POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\nContent-Length: 1\r\n\r\nx"
        notes = module(10).check_request(request)
        self.assertTrue(any("Transfer-Encoding with Content-Length" in n for n in notes))
        self.assertTrue(any("body is not decoded" in n for n in notes))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Revision-specific boundary regressions for direct APIs and signed claims."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def lab(n):
    src = sorted((ROOT / "projects").glob("[0-9][0-9]_*.py"))[n-1]
    spec = importlib.util.spec_from_file_location("revised_" + str(n), src)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

class RevisedBoundaries(unittest.TestCase):
    def test_path_guard_invalid_direct_mode(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            obj=lab(4); obj.choose(obj.ROOT, "../secret.txt", "safee")

    def test_sql_invalid_direct_mode_not_unsafe(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            lab(5).find_accounts("safee", "' OR 1=1 --")

    def test_spray_invalid_direct_mode_not_unprotected(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            lab(6).simulate("protectd")

    def test_access_invalid_direct_mode(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            lab(8).check_access("safee", "alice", "notes", "read")

    def test_signed_payload_wrong_user_type(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":"viewer", "user":12},sort_keys=True,separators=(",",":")).encode("ascii"))
        with self.assertRaisesRegex(ValueError,"user"):
            m.verify(data+"."+m.encode(m.sign(data)))

    def test_signed_payload_empty_user(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":"editor", "user":""},sort_keys=True,separators=(",",":")).encode("ascii"))
        with self.assertRaisesRegex(ValueError,"user"):
            m.verify(data+"."+m.encode(m.sign(data)))

    def test_signed_payload_non_string_role(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":None, "user":"alice"},sort_keys=True,separators=(",",":")).encode("ascii"))
        with self.assertRaisesRegex(ValueError,"role"):
            m.verify(data+"."+m.encode(m.sign(data)))

    def test_known_key_admin_still_valid_mac_not_authorization(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":"admin", "user":"alice"},sort_keys=True,separators=(",",":")).encode("ascii"))
        verified=m.verify(data+"."+m.encode(m.sign(data)))
        self.assertEqual(verified["role"],"admin")

    def test_user_type_boolean_rejected(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":"viewer", "user":True},sort_keys=True,separators=(",",":")).encode("ascii"))
        with self.assertRaisesRegex(ValueError,"user"):
            m.verify(data+"."+m.encode(m.sign(data)))

    def test_signed_role_length_bound(self):
        m=lab(7)
        data=m.encode(json.dumps({"role":"a"*50,"user":"bob"},sort_keys=True,separators=(",",":")).encode("ascii"))
        with self.assertRaisesRegex(ValueError,"role"):
            m.verify(data+"."+m.encode(m.sign(data)))

if __name__ == "__main__":
    unittest.main()

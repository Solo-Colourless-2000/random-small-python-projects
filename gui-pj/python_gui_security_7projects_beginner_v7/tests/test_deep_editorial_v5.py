"""Regression tests for new findings from the detailed manual/source review."""
import importlib.util
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    p = next((ROOT / 'projects').glob(f'{n:02d}_*.py'))
    spec = importlib.util.spec_from_file_location(f'gui_v5_{n}', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

class NewSemanticChecks(unittest.TestCase):
    def test_cookie_valid_trio_observed(self):
        mod = load(2)
        text = 'Set-Cookie: sid=abc; Secure; HttpOnly; SameSite=Lax'
        self.assertTrue(any('SEEN: Cookie sid' in x for x in mod.audit(mod.parse_headers(text), True)))

    def test_cookie_repeated_secure_must_be_reviewed(self):
        mod = load(2)
        text = 'Set-Cookie: sid=abc; Secure; Secure; HttpOnly; SameSite=Lax'
        self.assertTrue(any('CHECK: Cookie sid' in x and 'duplicate' in x for x in mod.audit(mod.parse_headers(text), True)))

    def test_cookie_repeated_httponly_must_be_reviewed(self):
        mod = load(2)
        text = 'Set-Cookie: sid=abc; Secure; HttpOnly; HttpOnly; SameSite=Lax'
        self.assertTrue(any('CHECK: Cookie sid' in x and 'duplicate' in x for x in mod.audit(mod.parse_headers(text), True)))

    def test_cookie_malformed_httponly_must_be_reviewed(self):
        mod = load(2)
        text = 'Set-Cookie: sid=abc; Secure; HttpOnly; HttpOnly=0; SameSite=Lax'
        self.assertTrue(any('CHECK: Cookie sid' in x and 'malformed' in x for x in mod.audit(mod.parse_headers(text), True)))

    def test_cookie_malformed_secure_must_be_reviewed(self):
        mod = load(2)
        text = 'Set-Cookie: sid=abc; Secure; Secure=0; HttpOnly; SameSite=Lax'
        self.assertTrue(any('CHECK: Cookie sid' in x and 'malformed' in x for x in mod.audit(mod.parse_headers(text), True)))

    def test_file_stable_hash(self):
        mod = load(5)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'file.txt'
            p.write_bytes(b'hello')
            self.assertEqual(mod.digest_file(p), '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824')

    def test_file_concurrent_metadata_change_rejected(self):
        mod = load(5)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'file.txt'
            p.write_bytes(b'hello')
            original = os.stat(p)
            changed = types.SimpleNamespace(**{
                key: getattr(original, key)
                for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')
            })
            changed.st_mtime_ns += 1
            with mock.patch.object(mod.os, 'fstat', side_effect=[original, changed]):
                with self.assertRaisesRegex(ValueError, 'changed while hashing'):
                    mod.digest_file(p)

    def test_file_same_size_wrong_hash_blocked_by_metadata(self):
        mod = load(5)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'file.txt'
            p.write_bytes(b'hello')
            original = os.stat(p)
            changed = types.SimpleNamespace(**{
                key: getattr(original, key)
                for key in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')
            })
            changed.st_ctime_ns += 1
            with mock.patch.object(mod.os, 'fstat', side_effect=[original, changed]):
                with self.assertRaisesRegex(ValueError, 'changed while hashing'):
                    mod.digest_file(p)

if __name__ == '__main__':
    unittest.main()

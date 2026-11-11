"""Tamper with a toy signed token and compare trusted/untrusted decoding."""
import base64
import binascii
import hashlib
import hmac
import json
import re
import sys

# Constant classroom key: never use this to protect real identities.
LAB_KEY = b"training-only-key-do-not-deploy"


def encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode(value):
    # Require the exact unpadded Base64URL form produced by encode().
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value) or len(value) % 4 == 1:
        raise ValueError("invalid Base64URL alphabet or length")
    raw = value.encode("ascii")
    decoded = base64.b64decode(raw + b"=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    if encode(decoded) != value:
        raise ValueError("non-canonical Base64URL encoding")
    return decoded


def sign(message):
    return hmac.new(LAB_KEY, message.encode("ascii"), hashlib.sha256).digest()


def create(user, role):
    payload = json.dumps({"user": user, "role": role}, sort_keys=True, separators=(",", ":"))
    encoded = encode(payload.encode("ascii"))
    return encoded + "." + encode(sign(encoded))


def inspect_untrusted(token):
    if len(token) > 512 or token.count(".") != 1:
        raise ValueError("invalid token format")
    payload_part = token.split(".", 1)[0]
    return json.loads(decode(payload_part).decode("ascii"))


def tamper(token, role):
    if token.count(".") != 1 or len(token) > 512:
        raise ValueError("invalid token format")
    payload = inspect_untrusted(token)
    if not isinstance(payload, dict) or set(payload) != {"role", "user"}:
        raise ValueError("unexpected payload")
    payload["role"] = role
    changed = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return encode(changed.encode("ascii")) + "." + token.split(".")[1]


def verify(token):
    if len(token) > 512 or token.count(".") != 1:
        raise ValueError("invalid token format")
    payload_part, signature_part = token.split(".")
    if not hmac.compare_digest(sign(payload_part), decode(signature_part)):
        raise ValueError("signature mismatch")
    payload = inspect_untrusted(token)
    if not isinstance(payload, dict) or set(payload) != {"role", "user"}:
        raise ValueError("unexpected payload")
    user, role = payload["user"], payload["role"]
    if not isinstance(user, str) or not user or len(user) > 32 or not user.isascii() or not user.isalnum():
        raise ValueError("invalid signed user")
    if not isinstance(role, str) or not role.isascii() or len(role) > 32:
        raise ValueError("invalid signed role type")
    # Valid MACs do not authorize roles. An attacker who knows LAB_KEY can sign admin.
    return payload


def main():
    args = sys.argv[1:]
    if len(args) == 3 and args[0] == "create":
        user, role = args[1:]
        if not user or len(user) > 32 or not user.isascii() or not user.isalnum() or role not in ("viewer", "editor"):
            print("Error: use ASCII alphanumeric user (1-32 chars) and viewer|editor")
            return 2
        print(create(user, role))
        return 0
    if len(args) == 3 and args[0] == "tamper" and args[2] in ("viewer", "editor", "admin"):
        try:
            print(tamper(args[1], args[2]))
            return 0
        except (ValueError, UnicodeError, binascii.Error, TypeError) as exc:
            print(f"INVALID: {exc}")
            return 1
    if len(args) == 2 and args[0] in ("inspect", "verify"):
        try:
            payload = inspect_untrusted(args[1]) if args[0] == "inspect" else verify(args[1])
            print(f"{'UNTRUSTED' if args[0] == 'inspect' else 'VALID'} user={payload['user']} role={payload['role']}")
            return 0
        except (ValueError, UnicodeError, binascii.Error, KeyError, TypeError) as exc:
            print(f"INVALID: {exc}")
            return 1
    print("Usage: python3 07_signed_token.py create USER viewer|editor | tamper TOKEN ROLE | inspect TOKEN | verify TOKEN")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

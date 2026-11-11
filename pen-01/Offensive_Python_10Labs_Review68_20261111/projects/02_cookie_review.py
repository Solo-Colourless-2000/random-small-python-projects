"""Review cookie attributes from saved Set-Cookie header lines."""
import re
import sys
from pathlib import Path

COOKIE_NAME = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"


def parse_cookie(line):
    prefix = "set-cookie:"
    if not line.lower().startswith(prefix):
        raise ValueError("expected Set-Cookie header")
    parts = [part.strip() for part in line[len(prefix):].split(";")]
    if "=" not in parts[0]:
        raise ValueError("missing cookie name=value")
    name, value = parts[0].split("=", 1)
    if not re.fullmatch(COOKIE_NAME, name):
        raise ValueError("invalid cookie name")
    if value.startswith('"') != value.endswith('"') or value == '"':
        raise ValueError("unbalanced cookie value quotes")
    plain_value = value[1:-1] if value.startswith('"') else value
    if any(not (ch.isascii() and (33 <= ord(ch) <= 126) and ch not in ',;\\"') for ch in plain_value):
        raise ValueError("invalid cookie value")
    attrs = {}
    for part in parts[1:]:
        if not part:
            continue
        key, _, setting = part.partition("=")
        key = key.lower().strip()
        if not re.fullmatch(COOKIE_NAME, key) or key in attrs or any(ord(ch) < 32 or ord(ch) == 127 for ch in setting):
            raise ValueError("invalid or duplicate cookie attribute")
        attrs[key] = setting.strip()
    return name.strip(), value, attrs


def review(name, attrs):
    warnings = []
    for flag in ("secure", "httponly"):
        if flag not in attrs:
            warnings.append(f"missing {flag}")
        elif attrs[flag] != "":
            warnings.append(f"unexpected {flag} flag value")
    # Browsers treat Secure as present even when a value is supplied.
    secure_present = "secure" in attrs
    same_site = attrs.get("samesite", "").lower()
    if same_site not in ("strict", "lax", "none"):
        warnings.append("missing or unknown samesite")
    if same_site == "none" and not secure_present:
        warnings.append("SameSite=None requires Secure in modern browsers")
    if name.startswith("__Secure-") and not secure_present:
        warnings.append("__Secure- prefix needs Secure")
    if name.startswith("__Host-"):
        if not secure_present or attrs.get("path") != "/" or "domain" in attrs:
            warnings.append("__Host- needs Secure, Path=/, no Domain")
    return warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 02_cookie_review.py file")
        return 2
    try:
        path = Path(sys.argv[1])
        if path.stat().st_size > 100_000:
            raise ValueError("file exceeds 100000 bytes")
        saved = path.read_bytes().decode("utf-8")
        # Split only LF and CRLF; a lone CR must not become another cookie line.
        if "\r" in saved.replace("\r\n", ""):
            raise ValueError("bare CR in saved Set-Cookie data")
        lines = [line for line in saved.replace("\r\n", "\n").split("\n") if line.strip()]
        if not lines:
            raise ValueError("no Set-Cookie lines")
        for line in lines:
            name, _, attrs = parse_cookie(line)
            warnings = review(name, attrs)
            print(f"{name}: " + ("REVIEW " + "; ".join(warnings) if warnings else "PASS basic flags"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

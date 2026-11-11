"""Review security response headers from an offline sample."""
import re
import sys
from pathlib import Path


def read_headers(path):
    if path.stat().st_size > 100_000:
        raise ValueError("header file exceeds 100000 bytes")
    fields = {}
    data = path.read_bytes().decode("utf-8")
    # Accept saved LF or CRLF line endings, but reject standalone CR bytes.
    if "\r" in data.replace("\r\n", ""):
        raise ValueError("bare CR in saved header data")
    # The first empty line ends the header block; the body is not a header.
    for line_number, raw in enumerate(data.replace("\r\n", "\n").split("\n"), 1):
        if line_number == 1 and raw.startswith("HTTP/"):
            if not re.fullmatch(r"HTTP/1\.[01] [1-5][0-9]{2}(?: [\x20-\x7e]*)?", raw):
                raise ValueError("invalid HTTP status line")
            continue
        if raw == "":
            break
        if raw[0].isspace() or ":" not in raw:
            raise ValueError("invalid header line")
        name, value = raw.split(":", 1)
        if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
            raise ValueError("invalid header name")
        if any(ord(ch) < 32 and ch != "\t" or ord(ch) == 127 for ch in value):
            raise ValueError("control character in header value")
        # RFC field values can be empty; an empty security policy still needs review.
        fields.setdefault(name.lower(), []).append(value.strip(" \t"))
    if not fields:
        raise ValueError("no response headers")
    return fields


def inspect(fields, scheme):
    notes = []
    for name, values in sorted(fields.items()):
        # Multiple Set-Cookie field lines are normal and must not be merged.
        if len(values) > 1 and name != "set-cookie":
            notes.append(f"REVIEW duplicate: {name}")
    csp = fields.get("content-security-policy", [])
    notes.append("REVIEW CSP: present, inspect directives" if any(csp) else "REVIEW CSP: missing or empty")
    nosniff = fields.get("x-content-type-options", [])
    notes.append("PASS nosniff" if len(nosniff) == 1 and nosniff[0].lower() == "nosniff" else "REVIEW nosniff")
    referrer = fields.get("referrer-policy", [])
    notes.append("REVIEW Referrer-Policy: present, inspect value" if any(referrer) else "REVIEW Referrer-Policy: missing or empty")
    if scheme == "https":
        sts = fields.get("strict-transport-security", [])
        notes.append("REVIEW HSTS: inspect max-age" if any(sts) else "REVIEW HSTS: missing or empty")
    else:
        notes.append("INFO HSTS: only meaningful over HTTPS")
    return notes


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in ("http", "https"):
        print("Usage: python3 01_header_audit.py file http|https")
        return 2
    try:
        fields = read_headers(Path(sys.argv[1]))
        for note in inspect(fields, sys.argv[2]):
            print(note)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

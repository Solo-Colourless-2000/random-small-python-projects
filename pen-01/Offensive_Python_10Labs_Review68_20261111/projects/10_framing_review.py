"""Flag ambiguous HTTP/1.1 request framing in an offline fixture."""
import sys
from pathlib import Path


FIELD_CHARS = b"!#$%&'" + b"*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def check_request(data):
    if b"\r\n\r\n" not in data:
        raise ValueError("missing CRLF header separator")
    header_bytes, body = data.split(b"\r\n\r\n", 1)
    lines = header_bytes.split(b"\r\n")
    if any(b"\r" in line or b"\n" in line for line in lines):
        raise ValueError("bare line break in header section")
    request_parts = lines[0].split(b" ")
    if (len(request_parts) != 3 or request_parts[0] not in (b"GET", b"POST", b"PUT")
            or not request_parts[1] or request_parts[2] != b"HTTP/1.1"):
        raise ValueError("expected HTTP/1.1 request line")
    if any(byte < 33 or byte > 126 for byte in request_parts[1]):
        raise ValueError("control or non-ASCII byte in request target")
    fields = {}
    for line in lines[1:]:
        if not line or line[:1] in (b" ", b"\t") or b":" not in line:
            raise ValueError("invalid or folded field line")
        name, value = line.split(b":", 1)
        if not name or any(ch not in FIELD_CHARS for ch in name):
            raise ValueError("invalid field name")
        if any(ch < 32 and ch != 9 or ch == 127 for ch in value):
            raise ValueError("control byte in field value")
        key = name.lower()
        fields.setdefault(key, []).append(value.strip())
    notes = []
    if len(fields.get(b"host", [])) != 1 or not fields[b"host"][0]:
        notes.append("REVIEW missing or repeated Host header")
    lengths = fields.get(b"content-length", [])
    transfers = fields.get(b"transfer-encoding", [])
    if len(lengths) > 1:
        notes.append("REVIEW duplicate Content-Length fields")
    if transfers and lengths:
        notes.append("REVIEW Transfer-Encoding with Content-Length")
    if len(transfers) > 1:
        notes.append("REVIEW duplicate Transfer-Encoding fields")
    for value in lengths:
        if not value.isascii() or not value.isdigit() or len(value) > 12:
            notes.append("REVIEW malformed or oversized Content-Length")
        elif not transfers and int(value) != len(body):
            notes.append("REVIEW Content-Length does not match saved body bytes")
    for value in transfers:
        if value.lower() != b"chunked":
            notes.append("REVIEW unfamiliar Transfer-Encoding value")
    if transfers:
        # This small checker does not parse chunk sizes, trailers, or terminators.
        notes.append("REVIEW Transfer-Encoding body is not decoded or validated")
    if body and not lengths and not transfers:
        notes.append("REVIEW extra bytes without Content-Length or Transfer-Encoding")
    return notes or ["No basic framing conflict detected (not a full parser)"]


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 10_framing_review.py request_file")
        return 2
    try:
        path = Path(sys.argv[1])
        if path.stat().st_size > 100_000:
            raise ValueError("request exceeds 100000 bytes")
        for message in check_request(path.read_bytes()):
            print(message)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

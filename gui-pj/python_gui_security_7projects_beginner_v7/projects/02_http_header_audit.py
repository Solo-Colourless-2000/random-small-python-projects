"""Review pasted HTTP response headers without opening a network connection."""
import re
import tkinter as tk
from tkinter import ttk

MAX_TEXT = 16000
HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


def parse_headers(text):
    """Keep repeated header names; reject folded or broken lines."""
    if len(text) > MAX_TEXT:
        raise ValueError("Header text is too long.")
    headers = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip("\r")
        if not line:
            continue
        if number == 1 and re.fullmatch(r"HTTP/(?:1\.[01]|2|3) [1-5][0-9]{2}(?: [^\r\n]*)?", line):
            continue
        if line[:1].isspace() or ":" not in line:
            raise ValueError(f"Invalid header at line {number}.")
        name, value = line.split(":", 1)
        name = name.lower()
        if not HEADER_NAME.fullmatch(name):
            raise ValueError(f"Invalid header name at line {number}.")
        if any((ord(char) < 32 and char != "\t") or ord(char) == 127 for char in value):
            raise ValueError(f"Control character at line {number}.")
        headers.setdefault(name, []).append(value.strip())
    if not headers:
        raise ValueError("Paste at least one response header field.")
    return headers


def audit(headers, is_https):
    """Return learning prompts, not a vulnerability verdict."""
    findings = []
    expected = {
        "content-security-policy": "CSP limits resource loading; policy quality needs review.",
        "x-content-type-options": "Consider nosniff to reduce MIME confusion.",
        "referrer-policy": "Consider a deliberate referrer policy.",
    }
    for name, explanation in expected.items():
        values = headers.get(name, [])
        if not values:
            findings.append(f"CHECK: Missing {name}. {explanation}")
        elif not any(value.strip() for value in values):
            findings.append(f"CHECK: {name} has no effective value.")
        elif name == "x-content-type-options" and (
                len(values) != 1 or values[0].strip().lower() != "nosniff"):
            findings.append("CHECK: X-Content-Type-Options needs exactly one nosniff value.")
        else:
            findings.append(f"SEEN: {name} ({len(values)} line(s)); inspect its policy.")
    if is_https:
        hsts = headers.get("strict-transport-security", [])
        if not hsts:
            findings.append("CHECK: Missing HSTS on an HTTPS response.")
        elif len(hsts) != 1:
            findings.append("CHECK: Multiple HSTS fields; review the ambiguity.")
        else:
            directives = [part.strip() for part in hsts[0].split(";")]
            age_items = [re.fullmatch(r"max-age\s*=\s*([0-9]+)", part, re.I)
                         for part in directives
                         if re.match(r"max-age(?:\s|=|$)", part, re.I)]
            if (len(age_items) != 1 or age_items[0] is None
                    or not any(char != "0" for char in age_items[0].group(1))):
                findings.append("CHECK: HSTS needs one unambiguous positive integer max-age.")
            else:
                findings.append("SEEN: HSTS has one positive max-age; other directives need review.")
    else:
        findings.append("NOTE: HSTS assessment skipped for a non-HTTPS context.")
    for value in headers.get("set-cookie", []):
        parts = [part.strip().lower() for part in value.split(";")]
        flags = set(parts[1:])
        attribute_names = [part.partition("=")[0].strip() for part in parts[1:] if part]
        name = value.split("=", 1)[0].strip() or "(unnamed)"
        missing = [flag for flag in ("secure", "httponly") if flag not in flags]
        if any(attribute_names.count(flag) > 1 for flag in ("secure", "httponly", "samesite")):
            missing.append("duplicate security attributes")
        if any(part.startswith(("secure=", "httponly=")) for part in parts[1:]):
            missing.append("malformed Secure/HttpOnly attribute")
        if "=" not in parts[0] or not HEADER_NAME.fullmatch(name):
            missing.append("valid cookie name/value syntax")
        same_site = [part.partition("=")[2].strip() for part in parts[1:]
                     if part.startswith("samesite=")]
        if len(same_site) != 1 or same_site[0] not in {"strict", "lax", "none"}:
            missing.append("valid samesite")
        if same_site == ["none"] and "secure" not in flags:
            missing.append("secure with SameSite=None")
        if missing:
            findings.append(f"CHECK: Cookie {name}: examine {', '.join(missing)}.")
        else:
            findings.append(f"SEEN: Cookie {name}: recognized flags (context matters).")
    findings.append("LIMIT: These checks do not establish whether a site is secure.")
    return findings


def launch():
    root = tk.Tk()
    root.title("HTTP Header Review Desk")
    root.geometry("850x650")
    pane = ttk.Frame(root, padding=14)
    pane.pack(fill="both", expand=True)
    ttk.Label(pane, text="Paste response headers (offline)", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(pane, text="No requests are sent. Treat pasted data as untrusted.").pack(anchor="w")
    source = tk.Text(pane, height=13, wrap="none")
    source.pack(fill="both", expand=True, pady=8)
    source.insert("1.0", "HTTP/1.1 200 OK\nContent-Type: text/html\nSet-Cookie: sid=example; Path=/\n")
    https = tk.BooleanVar(value=True)
    ttk.Checkbutton(pane, text="Assume this response came over HTTPS", variable=https).pack(anchor="w")
    output = tk.Text(pane, height=12, wrap="word", state="disabled")
    output.pack(fill="both", expand=True, pady=8)

    def inspect():
        try:
            items = parse_headers(source.get("1.0", "end-1c"))
            result = "\n".join(audit(items, https.get()))
        except ValueError as error:
            result = f"INPUT ERROR: {error}"
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", result)
        output.configure(state="disabled")

    ttk.Button(pane, text="Analyze headers", command=inspect).pack(anchor="w")
    root.mainloop()


if __name__ == "__main__":
    launch()

"""Inspect pasted email headers as untrusted evidence, entirely offline."""
import tkinter as tk
from email import policy
from email.parser import Parser
from email.utils import getaddresses
import re
from tkinter import ttk

MAX_INPUT = 18000


DOMAIN = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\Z")


def domain_from_header(value):
    """Accept only one recognizable ASCII mailbox in a header field."""
    addresses = getaddresses([str(value)])
    if len(addresses) != 1:
        return ""
    address = addresses[0][1]
    if address.count("@") != 1:
        return ""
    local, domain = address.rsplit("@", 1)
    if not local or len(domain) > 253 or not DOMAIN.fullmatch(domain) or any(
            len(label) > 63 or label.startswith("-") or label.endswith("-")
            for label in domain.split(".")):
        return ""
    return domain.lower()


def analyze_email(raw):
    if len(raw) > MAX_INPUT:
        raise ValueError("Email header text is too long.")
    if not raw.strip():
        raise ValueError("Paste at least one email header field.")
    message = Parser(policy=policy.default).parsestr(raw, headersonly=True)
    from_lines = message.get_all("From", [])
    reply_lines = message.get_all("Reply-To", [])
    findings = []
    if len(from_lines) != 1:
        findings.append("CHECK: Expected exactly one From field; sender comparison skipped.")
        from_domain = ""
    else:
        from_domain = domain_from_header(from_lines[0])
        if not from_domain:
            findings.append("CHECK: Could not parse the sender domain.")
    if len(reply_lines) > 1:
        findings.append("CHECK: Multiple Reply-To fields; comparison skipped.")
    elif reply_lines:
        reply_domain = domain_from_header(reply_lines[0])
        if not reply_domain:
            findings.append("CHECK: Reply-To address cannot be parsed.")
        elif not from_domain:
            findings.append("CHECK: Reply-To comparison skipped: valid single From needed.")
        elif reply_domain != from_domain:
            findings.append(f"REVIEW: From domain {from_domain} differs from Reply-To {reply_domain}.")
        else:
            findings.append("SEEN: Reply-To uses the same exact domain as From.")
    else:
        findings.append("NOTE: No Reply-To field was supplied.")
    authentication = message.get_all("Authentication-Results", [])
    if authentication:
        findings.append("NOTE: Authentication-Results exists, but pasted text cannot validate it.")
    else:
        findings.append("NOTE: No Authentication-Results field in pasted data.")
    defects = list(message.defects)
    for field in message.values():
        defects.extend(getattr(field, "defects", ()))
    if defects:
        findings.append(f"CHECK: Parser reported {len(defects)} syntax defect(s).")
    findings.append("LIMIT: Domain mismatch is a clue, not proof of phishing.")
    return findings


def launch():
    root = tk.Tk()
    root.title("Email Header Clue Finder")
    root.geometry("830x610")
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Examine email headers without opening links", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Use invented sample headers; do not paste private mail.").pack(anchor="w")
    source = tk.Text(frame, height=13, wrap="none")
    source.pack(fill="both", expand=True, pady=10)
    source.insert("1.0", "From: Example Desk <help@example.test>\n"
                          "Reply-To: reply@support.example.test\n"
                          "Subject: Sample message\n")
    output = tk.Text(frame, height=10, wrap="word", state="disabled")
    output.pack(fill="both", expand=True, pady=10)

    def review():
        try:
            lines = analyze_email(source.get("1.0", "end-1c"))
            text = "\n".join(lines)
        except (ValueError, UnicodeError) as error:
            text = f"INPUT ERROR: {error}"
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", text)
        output.configure(state="disabled")

    ttk.Button(frame, text="Review headers", command=review).pack(anchor="w")
    root.mainloop()


if __name__ == "__main__":
    launch()

"""Twenty-four additional focused checks. Re-read all package files each pass.

This is automated scrutiny with explicit checks, not 24 human expert reviews.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = sorted((ROOT / "projects").glob("[0-9][0-9]_*.py"))
PAGE = ROOT / "Python_ペンテスト10作品_全行構文分解_20261111.html"
REPORT = ROOT / "verification/24_NEW_FOCUS_AUDIT.json"
SKIP_SUFFIXES = {".pyc"}


def module(index):
    spec = importlib.util.spec_from_file_location(f"focused_lab_{index}", PROJECTS[index - 1])
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def ensure(condition, reason):
    if not condition:
        raise AssertionError(reason)


def expect_error(fn, expected=ValueError):
    try:
        fn()
    except expected:
        return
    raise AssertionError(f"Expected {expected.__name__}")


def audit_one(n, file_bytes):
    sources = [file_bytes[p].decode("ascii") for p in PROJECTS]
    html = file_bytes[PAGE].decode("utf-8")
    if n == 1:
        ensure(len(PROJECTS) == 10 and [p.name[:2] for p in PROJECTS] == [f"{i:02d}" for i in range(1,11)], "numbered inventory")
    elif n == 2:
        ensure(all(s.isascii() and s.endswith("\n") for s in sources), "ASCII source/final newline")
    elif n == 3:
        ensure(all(ast.parse(s) for s in sources), "Python AST parse")
    elif n == 4:
        allowed = {"sys", "re", "pathlib", "socket", "threading", "urllib", "sqlite3", "contextlib", "base64", "binascii", "hashlib", "hmac", "json", "ipaddress", "struct"}
        imports = set()
        for s in sources:
            for node in ast.walk(ast.parse(s)):
                if isinstance(node, ast.Import):
                    imports.update(item.name.split(".")[0] for item in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
        ensure(imports <= allowed, "unexpected project dependency")
    elif n == 5:
        ensure(not any("subprocess" in s or "requests.get(" in s or "os.system(" in s for s in sources), "remote orchestration in project")
    elif n == 6:
        ensure(all(file_bytes[ROOT / "samples" / name] for name in ("response_headers.txt", "cookies.txt", "synthetic_traffic.pcap", "request_simple.http", "request_ambiguous.http")), "sample missing or empty")
    elif n == 7:
        ensure('HOST = "127.0.0.1"' in sources[2] and 'socket.create_connection((HOST, port)' in sources[2], "unfixed TCP target")
    elif n == 8:
        text = sources[1]
        ensure('saved = path.read_bytes().decode("utf-8")' in text and 'if "\\r" in saved.replace("\\r\\n", "")' in text, "Cookie line ending detection")
    elif n == 9:
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/"cookie.txt"
            p.write_bytes(b"Set-Cookie: x=1; Secure\rSet-Cookie: y=2; Secure\n")
            mod = module(2)
            with patch.object(mod.sys,"argv",["cookie.py",str(p)]), contextlib.redirect_stdout(io.StringIO()):
                ensure(mod.main()==1, "Cookie bare CR must fail")
    elif n == 10:
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/"cookie.txt"
            p.write_bytes(b"Set-Cookie: x=1; Secure; HttpOnly; SameSite=Lax\r\n")
            mod = module(2)
            out=io.StringIO()
            with patch.object(mod.sys,"argv",["cookie.py",str(p)]), contextlib.redirect_stdout(out):
                ensure(mod.main()==0 and "x: PASS" in out.getvalue(), "Cookie CRLF must succeed")
    elif n == 11:
        mod = module(3)
        with patch.object(mod.sys,"argv",["probe.py","check","1"*20000]),contextlib.redirect_stdout(io.StringIO()):
            ensure(mod.main()==2,"oversized port argument not rejected")
    elif n == 12:
        mod=module(3)
        with patch.object(mod.sys,"argv",["probe.py","check","123"]), patch.object(mod,"probe",return_value=("CLOSED/UNREACHABLE","")),contextlib.redirect_stdout(io.StringIO()):
            ensure(mod.main()==1,"closed TCP status exit code")
    elif n == 13:
        mod=module(4)
        ensure(mod.choose(mod.ROOT,"../secret.txt","unsafe").name=="secret.txt", "toy traversal demonstration")
        expect_error(lambda:mod.choose(mod.ROOT,"../secret.txt","safe"))
    elif n == 14:
        mod=module(5)
        ensure(mod.find_accounts("unsafe","' OR 1=1 --")==["alice","bob"] and mod.find_accounts("safe","' OR 1=1 --")==[], "SQL bound parameter contrast")
    elif n == 15:
        mod=module(6)
        with contextlib.redirect_stdout(io.StringIO()):
            ensure(mod.simulate("protected")== (2,["alice"]), "toy spraying cap")
    elif n == 16:
        mod=module(7)
        for value in (b"a",b"ab",b"abc",b"abcd",b"hello"):
            ensure(mod.decode(mod.encode(value))==value,"canonical Base64URL roundtrip")
    elif n == 17:
        mod=module(7)
        expect_error(lambda:mod.decode("e31"))
        expect_error(lambda:mod.decode("e30="))
        expect_error(lambda:mod.decode("+/8"))
    elif n == 18:
        mod=module(7)
        original=mod.create("alice","viewer")
        ensure(mod.verify(original)["role"]=="viewer","signed token original")
        expect_error(lambda:mod.verify(mod.tamper(original,"admin")))
    elif n == 19:
        mod=module(8)
        ensure(mod.check_access("unsafe","alice","notes","read") and not mod.check_access("safe","alice","notes","read"), "IDOR demonstration")
    elif n == 20:
        mod=module(9)
        lines=mod.parse_pcap(ROOT / "samples/synthetic_traffic.pcap")
        ensure(len(lines)==2 and lines[0].startswith("UDP") and lines[1].startswith("TCP"), "PCAP sample parsing")
    elif n == 21:
        mod=module(9)
        ensure("SKIP" in mod.summarize_frame(b"tiny"),"short Ethernet handling")
    elif n == 22:
        mod=module(10)
        req=b"POST / HTTP/1.1\r\nHost: localhost\r\n\r\nDATA"
        ensure(any("extra bytes" in m for m in mod.check_request(req)), "unframed HTTP body")
    elif n == 23:
        mod=module(10)
        req=b"POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\nNOT CHUNKS"
        ensure(any("not decoded" in m for m in mod.check_request(req)), "unvalidated TE must be marked")
    elif n == 24:
        mod=module(10)
        req=b"POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 4\r\n\r\nDATA"
        ensure(mod.check_request(req)==["No basic framing conflict detected (not a full parser)"], "valid CL must remain usable")
        ensure(html.count('class="chapter"')==20 and html.count('class="step"')==40, "manual chapter/step count")
        ensure(html.count('data-check=')==20, "manual completion check count")
    else:
        raise AssertionError("out of range")


def main():
    paths = [p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in SKIP_SUFFIXES and p != REPORT]
    paths.sort()
    results=[]
    total_bytes=0
    for n in range(1,25):
        content={p:p.read_bytes() for p in paths}
        byte_count=sum(len(v) for v in content.values())
        total_bytes+=byte_count
        try:
            audit_one(n, content)
        except Exception as exc:
            results.append({"pass":n,"status":"FAIL","problem":repr(exc),"files_read":len(paths),"bytes_read":byte_count})
        else:
            results.append({"pass":n,"status":"PASS","files_read":len(paths),"bytes_read":byte_count})
    summary={"scope":"24 different automated additional checks; every checked file reread each pass", "total_passes":24, "passes":sum(v['status']=="PASS" for v in results), "files_per_pass":len(paths),"aggregate_bytes_read":total_bytes,"details":results}
    REPORT.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(f"NEW_FOCUS_CHECKS={len(results)} PASS={summary['passes']} FILES_READ_EACH_PASS={len(paths)}")
    print(f"AGGREGATE_BYTES_READ={total_bytes}")
    for item in results:
        if item['status']!='PASS':print("FAIL",item)
    return 0 if summary['passes']==24 else 1


if __name__=="__main__":
    raise SystemExit(main())

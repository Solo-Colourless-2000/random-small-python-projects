"""35 independent, focused semantic checks with a fresh complete-file read.

Designed as an executable supplement to the written editorial record.
A passing check is NOT equivalent to a human reading every word 35 times.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(number):
    path = next((ROOT / 'projects').glob(number + '_*.py'))
    spec = importlib.util.spec_from_file_location('semantic_' + number, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def requires_error(fn, error_type=ValueError):
    try:
        fn()
    except error_type:
        return
    raise AssertionError('Expected an error; none occurred')


def csv_file(text):
    with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write(text)
        return Path(f.name)


def csv_check(module, reader, csv_text, should_error=False):
    path=csv_file(csv_text)
    try:
        if should_error: requires_error(lambda: reader(path))
        else: return reader(path)
    finally:
        path.unlink()


checks = []

def add(project, label, action):
    checks.append((project,label,action))


a = load('01')
add('01','Six sample log events are parsed',lambda: assert_true(len(a.read_events(ROOT/'samples/auth_events.csv'))==6))
add('01','Three failures remain after a success',lambda: assert_true(a.summarize(a.read_events(ROOT/'samples/auth_events.csv'))[1]['198.51.100.8']==3))
add('01','Searching bob changes only visibility',lambda: assert_true(len(a.summarize(a.read_events(ROOT/'samples/auth_events.csv'),'bob')[0])==2 and a.summarize(a.read_events(ROOT/'samples/auth_events.csv'),'bob')[1]['198.51.100.8']==3))
add('01','Invalid IPv4 is rejected',lambda: csv_check(a,a.read_events,'timestamp,username,ip,status\n2026-11-10,alice,192.0.2.999,FAIL\n',True))
add('01','CSV bytes and row bounds are explicit',lambda: assert_true(a.MAX_CSV_BYTES==1048576 and a.MAX_ROWS==1000))

b=load('02')
add('02','Large positive HSTS age cannot crash int conversion',lambda: assert_true(any(x.startswith('SEEN: HSTS') for x in b.audit(b.parse_headers('Strict-Transport-Security: max-age='+'9'*5000),True))))
add('02','Large zero HSTS age does not appear positive',lambda: assert_true(any(x.startswith('CHECK: HSTS') for x in b.audit(b.parse_headers('Strict-Transport-Security: max-age='+'0'*5000),True))))
add('02','Conflicting HSTS directives trigger review',lambda: assert_true(any(x.startswith('CHECK: HSTS') for x in b.audit(b.parse_headers('Strict-Transport-Security: max-age=1; max-age=2'),True))))
add('02','Blank pasted header text is input error',lambda: requires_error(lambda:b.parse_headers('\n  \n')))
add('02','SameSite None without Secure triggers review',lambda: assert_true(any('secure with SameSite=None' in x for x in b.audit(b.parse_headers('Set-Cookie: sid=x; HttpOnly; SameSite=None'),True))))

c=load('03')
add('03','Sample contains five rows and three review candidates',lambda: assert_true(len(c.read_rules(ROOT/'samples/firewall_rules.csv'))==5 and sum(c.assess(x).startswith('REVIEW') for x in c.read_rules(ROOT/'samples/firewall_rules.csv'))==3))
add('03','Unaligned CIDR fails, rather than silently broadening source',lambda: csv_check(c,c.read_rules,'protocol,port,source,action\nTCP,22,192.0.2.17/24,ALLOW\n',True))
add('03','Aligned /24 network is accepted',lambda: assert_true(csv_check(c,c.read_rules,'protocol,port,source,action\nTCP,22,192.0.2.0/24,ALLOW\n')[0]['source']=='192.0.2.0/24'))
add('03','Port 65536 is rejected before policy review',lambda: csv_check(c,c.read_rules,'protocol,port,source,action\nTCP,65536,::/0,ALLOW\n',True))
add('03','Sample IPv6 broad allow remains review candidate',lambda: assert_true(any(x['source']=='::/0' and c.assess(x).startswith('REVIEW') for x in c.read_rules(ROOT/'samples/firewall_rules.csv'))))

d=load('04')
add('04','All three expected IOC matches appear',lambda: assert_true(len(d.correlate(d.load_csv(ROOT/'samples/indicators.csv',('type','value')),d.load_csv(ROOT/'samples/ioc_events.csv',('timestamp','ip','domain','sha256'))))==3))
add('04','Zone-qualified IPv6 is rejected as IOC',lambda: requires_error(lambda:d.normalize('ip','fe80::1%eth0')))
add('04','Trailing domain dot and case are normalized',lambda: assert_true(d.normalize('domain','EXAMPLE.TEST.')=='example.test'))
add('04','Short SHA-256 is rejected',lambda: requires_error(lambda:d.normalize('sha256','a'*63)))
add('04','IOC CSV input has a bounded file size',lambda: assert_true(d.MAX_CSV_BYTES==1048576))

e=load('05')
add('05','Integrity sample contains two direct files',lambda: assert_true(set(e.snapshot(ROOT/'samples/integrity_folder'))=={'config.txt','readme.txt'}))
add('05','Changed digest is classified as MODIFIED',lambda: assert_true(e.compare({'config.txt':'a'},{'config.txt':'b'})==[('config.txt','MODIFIED')]))

def symlink_check():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        (root/'real.txt').write_text('hello',encoding='utf-8')
        (root/'link.txt').symlink_to(root/'real.txt')
        assert_true(set(e.snapshot(root))=={'real.txt'})
add('05','Symlink is excluded from snapshots',symlink_check)

def oversized_check():
    with tempfile.TemporaryDirectory() as directory:
        p=Path(directory)/'huge.bin'
        p.write_bytes(b'x'*(e.MAX_SIZE+1))
        requires_error(lambda:e.snapshot(directory))
add('05','Over-five-MiB file causes a clear failure',oversized_check)
add('05','Comparisons distinguish addition and removal',lambda: assert_true(e.compare({'a':'1'},{'b':'2'})==[('a','REMOVED'),('b','ADDED')]))

f=load('06')
add('06','Sample From/Reply-To discrepancy yields REVIEW',lambda: assert_true(any(x.startswith('REVIEW:') for x in f.analyze_email((ROOT/'samples/mail_headers.txt').read_text()))))
add('06','Duplicate From never produces same-domain SEEN',lambda: assert_true(not any(x.startswith('SEEN: Reply-To') for x in f.analyze_email('From: a@example.test\nFrom: b@example.test\nReply-To: c@example.test\n'))))
add('06','Duplicate Reply-To never produces same-domain SEEN',lambda: assert_true(not any(x.startswith('SEEN: Reply-To') for x in f.analyze_email('From: a@example.test\nReply-To: b@example.test\nReply-To: a@example.test\n'))))
add('06','Authentication-Results is not treated as verified fact',lambda: assert_true(any('cannot validate it' in x for x in f.analyze_email('From: a@example.test\nAuthentication-Results: attacker.invalid; spf=pass\n'))))
add('06','Single valid From and Reply-To same-domain is SEEN',lambda: assert_true(any(x.startswith('SEEN: Reply-To') for x in f.analyze_email('From: a@example.test\nReply-To: b@example.test\n'))))

g=load('07')
def locked():
    t=g.Throttle()
    for _ in range(3):r=t.attempt('FAIL')
    assert_true(r.startswith('LOCKED') and t.lock_until==30)
add('07','Third failure triggers lock_until at t=30',locked)
def boundary():
    t=g.Throttle()
    for _ in range(3):t.attempt('FAIL')
    t.advance(20)
    assert_true(t.attempt('SUCCESS').startswith('BLOCKED'))
    t.advance(10)
    assert_true(t.attempt('SUCCESS').startswith('Allowed'))
add('07','Lock is blocked at t=20 and released at t=30',boundary)
def expiry():
    t=g.Throttle();t.attempt('FAIL');t.advance(60)
    assert_true(t.attempt('FAIL').endswith('(1 of 3).'))
add('07','Failure falls out of the 60 second time window',expiry)
add('07','Negative time advance is rejected',lambda:requires_error(lambda:g.Throttle().advance(-1)))
add('07','No user credentials or remote traffic in the simulation',lambda:assert_true('import socket' not in (ROOT/'projects/07_login_throttle_lab.py').read_text() and 'getpass' not in (ROOT/'projects/07_login_throttle_lab.py').read_text().lower()))


def assert_true(condition):
    if not condition:raise AssertionError('Criterion not met')


def main():
    assert len(checks)==35,len(checks)
    for index,(project,label,action) in enumerate(checks,1):
        # Re-open every item, not only a copy held from an earlier review.
        digest=hashlib.sha256()
        for file in sorted(ROOT.rglob('*')):
            if not file.is_file() or '__pycache__' in file.parts:
                continue
            digest.update(str(file.relative_to(ROOT)).encode('utf-8'))
            digest.update(file.read_bytes())
        action()
        print(f'{index:02d}. PASS | Project {project} | {label} | snapshot {digest.hexdigest()[:12]}')
    print('35 / 35 thematic semantic checks PASSED')

if __name__=='__main__':main()

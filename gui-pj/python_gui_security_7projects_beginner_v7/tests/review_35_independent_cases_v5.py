"""35 targeted fresh counterexamples / boundary checks for the v5 editorial review.

This supplements close reading; it does not pretend to be 35 human rereadings.
"""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import os

ROOT=Path(__file__).resolve().parents[1]

def module(n):
    path=next((ROOT/'projects').glob(f'{n:02d}_*.py'))
    spec=importlib.util.spec_from_file_location(f'audit_v5_{n}',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def must_fail(func):
    try:func()
    except ValueError:return
    raise AssertionError('Expected ValueError')

def csv_input(callback,text):
    with TemporaryDirectory() as folder:
        p=Path(folder)/'input.csv';p.write_text(text,encoding='utf-8-sig')
        return callback(p)

def check(expr):
    assert expr, 'Condition not met'

a=module(1);b=module(2);c=module(3);d=module(4);e=module(5);f=module(6);g=module(7)
checks=[]
def add(project,name,fn):checks.append((project,name,fn))
# 01 - CSV semantics and evidence interpretation.
head='timestamp,username,ip,status\n'
add(1,'BOM-encoded sample row parses',lambda:check(len(csv_input(a.read_events,head+'t,alice,192.0.2.1,FAIL\n'))==1))
add(1,'Duplicated header columns are rejected',lambda:must_fail(lambda:csv_input(a.read_events,'timestamp,username,ip,ip\nt,a,192.0.2.1,FAIL\n')))
add(1,'Lowercase fail is intentionally rejected',lambda:must_fail(lambda:csv_input(a.read_events,head+'t,alice,192.0.2.1,fail\n')))
add(1,'IPv6 equivalent compressed text is normalized',lambda:check(csv_input(a.read_events,head+'t,a,2001:db8:0:0:0:0:0:1,FAIL\n')[0]['ip']=='2001:db8::1'))
add(1,'Filter is casefolded but full failure counts remain',lambda:check(len(a.summarize(csv_input(a.read_events,head+'t,Alice,192.0.2.1,FAIL\nt,Bob,192.0.2.1,FAIL\n'),'ALICE')[0])==1 and a.summarize(csv_input(a.read_events,head+'t,Alice,192.0.2.1,FAIL\nt,Bob,192.0.2.1,FAIL\n'),'ALICE')[1]['192.0.2.1']==2))
# 02 - distinguish observed flags from ambiguous or malformed attributes.
def cookie(x):return '\n'.join(b.audit(b.parse_headers('Set-Cookie: '+x),True))
add(2,'Valid Secure HttpOnly SameSite is only SEEN',lambda:check('SEEN: Cookie sid:' in cookie('sid=1; Secure; HttpOnly; SameSite=Lax')))
add(2,'Duplicate Secure cannot appear merely SEEN',lambda:check('duplicate security attributes' in cookie('sid=1; Secure; Secure; HttpOnly; SameSite=Lax')))
add(2,'Duplicate HttpOnly cannot appear merely SEEN',lambda:check('duplicate security attributes' in cookie('sid=1; Secure; HttpOnly; HttpOnly; SameSite=Lax')))
add(2,'HttpOnly=false is malformed when a proper flag also exists',lambda:check('malformed Secure/HttpOnly' in cookie('sid=1; Secure; HttpOnly; HttpOnly=false; SameSite=Lax')))
add(2,'SameSite=None without Secure is reviewed',lambda:check('secure with SameSite=None' in cookie('sid=1; HttpOnly; SameSite=None')))
# 03 - networking scope and input validation.
def rules(line):return csv_input(c.read_rules,'protocol,port,source,action\n'+line+'\n')
add(3,'Port upper bound 65535 is permitted',lambda:check(rules('TCP,65535,192.0.2.0/24,ALLOW')[0]['port']=='65535'))
add(3,'Port zero is rejected',lambda:must_fail(lambda:rules('TCP,0,192.0.2.0/24,ALLOW')))
add(3,'Wildcard any is accepted without int conversion',lambda:check(c.assess(rules('UDP,any,::/0,ALLOW')[0]).startswith('REVIEW')))
add(3,'Superscript numeral cannot be used as port',lambda:must_fail(lambda:rules('TCP,²,0.0.0.0/0,ALLOW')))
add(3,'Deny broad access is not a broad ALLOW warning',lambda:check(c.assess(rules('TCP,22,0.0.0.0/0,DENY')[0])=='DENY rule'))
# 04 - exact IOC matching and correct normalization.
add(4,'Trailing dot can be normalized',lambda:check(d.normalize('domain','CASE.EXAMPLE.TEST.')=='case.example.test'))
add(4,'Consecutive dots rejected',lambda:must_fail(lambda:d.normalize('domain','a..example.test')))
add(4,'Hyphen-ended DNS label rejected',lambda:must_fail(lambda:d.normalize('domain','abc-.example.test')))
add(4,'Uppercase hex SHA-256 canonicalized',lambda:check(d.normalize('sha256','AB'*32)=='ab'*32))
def two_hits():
    s='ab'*32
    m=d.correlate([{'type':'ip','value':'192.0.2.1'},{'type':'sha256','value':s}],[{'timestamp':'t','ip':'192.0.2.1','domain':'','sha256':s}])
    check(len(m)==2 and {x[1] for x in m}=={'ip','sha256'})
add(4,'One event can produce two match rows',two_hits)
# 05 - filesystem behaviour, hash validity and race disclaimer.
def temporary_file(fn):
    with TemporaryDirectory() as folder:
        p=Path(folder)/'f.txt';p.write_bytes(b'hello');fn(p)
add(5,'Stable file hashes deterministically',lambda:temporary_file(lambda p:check(e.digest_file(p)==e.digest_file(p))))
add(5,'Modified contents become MODIFIED',lambda:check(e.compare({'a':'aaa'},{'a':'bbb'})==[('a','MODIFIED')]))
add(5,'Same contents after restoration become UNCHANGED',lambda:check(e.compare({'a':'aaa'},{'a':'aaa'})==[('a','UNCHANGED')]))
def race_case(path,attribute):
    before=os.stat(path)
    keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode')
    after=SimpleNamespace(**{key:getattr(before,key) for key in keys})
    setattr(after,attribute,getattr(after,attribute)+1)
    with patch.object(e.os,'fstat',side_effect=[before,after]):must_fail(lambda:e.digest_file(path))
add(5,'Changed size during hashing is detected',lambda:temporary_file(lambda p:race_case(p,'st_size')))
add(5,'Changed mtime during hashing is detected',lambda:temporary_file(lambda p:race_case(p,'st_mtime_ns')))
# 06 - never call untrusted header text authenticated.
add(6,'No From field makes comparison undecidable',lambda:check(any('From field' in x for x in f.analyze_email('Reply-To: x@example.test\n'))))
add(6,'Duplicate From is an explicit CHECK',lambda:check(any('exactly one From' in x for x in f.analyze_email('From: a@example.test\nFrom: b@example.test\nReply-To: a@example.test\n'))))
add(6,'Duplicate Reply-To is an explicit CHECK',lambda:check(any('Multiple Reply-To' in x for x in f.analyze_email('From: a@example.test\nReply-To: a@example.test\nReply-To: b@example.test\n'))))
add(6,'Single matching domains yield only a clue',lambda:check(any(x.startswith('SEEN: Reply-To') for x in f.analyze_email('From: a@example.test\nReply-To: b@example.test\n'))))
add(6,'Authentication-Results presence is not validation',lambda:check(any('cannot validate it' in x for x in f.analyze_email('From: a@example.test\nAuthentication-Results: fake.invalid; spf=pass\n'))))
# 07 - account lockout timeline.
add(7,'Two failures are insufficient for lock',lambda:check(g.Throttle().attempt('FAIL')=='Recorded failure (1 of 3).'))
def locked_after_three():
    t=g.Throttle();[t.attempt('FAIL') for _ in range(3)];check(t.lock_until==30)
add(7,'Three failures cause 30-second lock',locked_after_three)
def blocked_at_twenty():
    t=g.Throttle();[t.attempt('FAIL') for _ in range(3)];t.advance(20);check('BLOCKED' in t.attempt('SUCCESS'))
add(7,'Success attempt is blocked during lock',blocked_at_twenty)
def released_at_thirty():
    t=g.Throttle();[t.attempt('FAIL') for _ in range(3)];t.advance(30);check('Allowed' in t.attempt('SUCCESS'))
add(7,'Exact lock boundary is released',released_at_thirty)
def success_clear():
    t=g.Throttle();t.attempt('FAIL');t.attempt('SUCCESS');check(not t.fail_times)
add(7,'Successful attempt clears old failures',success_clear)

if __name__=='__main__':
    assert len(checks)==35,len(checks)
    for idx,(project,label,fn) in enumerate(checks,1):
        fn();print(f'{idx:02d} PASS P{project:02d}: {label}')
    print('35 / 35 NEW editorial scenario checks passed')

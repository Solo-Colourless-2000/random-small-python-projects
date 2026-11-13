"""36 named and different v6 editorial audits; not 36 full human rereadings.

These test actual invariants and adversarial inputs across all seven projects,
plus tutorial/source integrity, accessibility and in-document links.
"""
from __future__ import annotations
import importlib.util
import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
MANUAL=ROOT/'Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'
S=BeautifulSoup(MANUAL.read_text(encoding='utf8'),'html.parser')

def load(n):
 p=next((ROOT/'projects').glob(f'{n:02d}_*.py'))
 spec=importlib.util.spec_from_file_location('audit_project_'+str(n),p)
 mod=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(mod)
 return mod

def csvtmp(folder,name,txt):
 p=Path(folder)/name
 p.write_text(txt,encoding='utf-8')
 return p

class V6ThirtySixAudits(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.m={n:load(n) for n in range(1,8)}

 # 01..08: file and manual integrity
 def test_01_exactly_seventeen_nav_chapters(self):
  chapters=S.select('section.chapter')
  self.assertEqual(17,len(chapters))
  self.assertEqual({f'p{n:02d}' for n in range(1,8)},set(c['id'] for c in chapters if re.fullmatch(r'p\d\d',c['id'])))
 def test_02_all_28_steps_match_source_bytes(self):
  for n in range(1,8):
   actual=next((ROOT/'projects').glob(f'{n:02d}_*.py')).read_text(encoding='utf8')
   code=''.join(step.get_text() for step in S.select(f'#p{n:02d} .step code[data-kind="python"]'))
   self.assertEqual(actual,code,f'step concatenation differs: {n}')
 def test_03_line_rows_cover_nonblank_source(self):
  for n in range(1,8):
   source=next((ROOT/'projects').glob(f'{n:02d}_*.py')).read_text(encoding='utf8').splitlines()
   for i,line in enumerate(source,1):
    row=S.select_one(f'#v6-line-{n:02d}-{i}')
    if line.strip():
     self.assertIsNotNone(row,(n,i))
     self.assertEqual(line,row.select_one('code.line-source').get_text(),(n,i))
     self.assertTrue(row.select_one('td:nth-of-type(2)').get_text(strip=True))
     self.assertTrue(row.select_one('td:nth-of-type(3)').get_text(strip=True))
    else:self.assertIsNone(row,(n,i))
 def test_04_every_line_has_distinct_anchor(self):
  ids=[e['id'] for e in S.select('[id]')]
  self.assertEqual(len(ids),len(set(ids)))
 def test_05_search_results_have_destinations(self):
  for e in S.select('[data-find]'): self.assertTrue(e.get('id'))
 def test_06_all_internal_hash_links_resolve(self):
  ids={e['id'] for e in S.select('[id]')}
  for a in S.select('a[href^="#"]'):
   if len(a['href'])>1:self.assertIn(a['href'][1:],ids)
 def test_07_all_35_focus_examples_appear_in_source(self):
  for n in range(1,8):
   text=next((ROOT/'projects').glob(f'{n:02d}_*.py')).read_text(encoding='utf8')
   examples=S.select(f'#v6-focus-{n:02d} .focus-code code')
   self.assertEqual(5,len(examples))
   for example in examples:self.assertIn(example.get_text(),text)
 def test_08_screenshots_and_sample_data_referenced_exist(self):
  for image in S.select('img[src^="images/"]'):
   self.assertTrue((ROOT/image['src']).is_file(),image['src'])
  self.assertEqual(7,len(S.select('#p01 img, #p02 img, #p03 img, #p04 img, #p05 img, #p06 img, #p07 img')))
  for f in ['auth_events.csv','response_headers.txt','firewall_rules.csv','indicators.csv','ioc_events.csv','mail_headers.txt']:
   self.assertTrue((ROOT/'samples'/f).is_file())

 # 09..12: authentication logs
 def test_09_auth_sample_count_three_failures(self):
  m=self.m[1]; events=m.read_events(ROOT/'samples/auth_events.csv')
  vis,failures=m.summarize(events)
  self.assertEqual(6,len(vis));self.assertEqual(3,failures['198.51.100.8'])
 def test_10_auth_filter_does_not_change_fail_counts(self):
  m=self.m[1];events=m.read_events(ROOT/'samples/auth_events.csv')
  vis,a=m.summarize(events,'bob');self.assertEqual(2,len(vis))
  self.assertEqual(a,m.summarize(events,'alice')[1])
 def test_11_auth_invalid_ip_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=csvtmp(d,'bad.csv','timestamp,username,ip,status\n2026,a,300.1.2.3,FAIL\n')
   with self.assertRaises(ValueError):self.m[1].read_events(p)
 def test_12_auth_duplicate_csv_column_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=csvtmp(d,'bad.csv','timestamp,ip,ip,status\n2026,1,2,FAIL\n')
   with self.assertRaises(ValueError):self.m[1].read_events(p)

 # 13..17: response headers
 def test_13_http_parses_repeated_fields_as_lists(self):
  h=self.m[2].parse_headers('Set-Cookie: a=1\nSet-Cookie: b=2\n')
  self.assertEqual(['a=1','b=2'],h['set-cookie'])
 def test_14_http_rejects_folded_continuation_line(self):
  with self.assertRaises(ValueError):self.m[2].parse_headers('Server: test\n continued\n')
 def test_15_http_catches_conflicting_cookie_attributes(self):
  m=self.m[2]
  t='Set-Cookie: sid=1; Secure; Secure=0; HttpOnly; SameSite=Lax\n'
  self.assertTrue(any(x.startswith('CHECK: Cookie') for x in m.audit(m.parse_headers(t),True)))
 def test_16_http_rejects_duplicate_hsts(self):
  m=self.m[2]
  h=m.parse_headers('Strict-Transport-Security: max-age=10\nStrict-Transport-Security: max-age=20\n')
  self.assertTrue(any('Multiple HSTS' in x for x in m.audit(h,True)))
 def test_17_http_missing_hsts_non_https_not_flagged(self):
  m=self.m[2];h=m.parse_headers('X-Content-Type-Options: nosniff\n')
  text='\n'.join(m.audit(h,False))
  self.assertIn('HSTS assessment skipped',text)
  self.assertNotIn('Missing HSTS',text)

 # 18..21: firewall rules
 def test_18_firewall_ipv4_any_source_requires_review(self):
  m=self.m[3]
  self.assertEqual('REVIEW: broad sensitive access',m.assess({'source':'0.0.0.0/0','port':'any','action':'ALLOW'}))
 def test_19_firewall_ipv6_deny_rule_not_accepted_as_allow(self):
  m=self.m[3]
  self.assertEqual('DENY rule',m.assess({'source':'::/0','port':'22','action':'DENY'}))
 def test_20_firewall_rejects_hostbits_as_network(self):
  with tempfile.TemporaryDirectory() as d:
   p=csvtmp(d,'x.csv','protocol,port,source,action\nTCP,22,10.0.0.1/24,ALLOW\n')
   with self.assertRaises(ValueError):self.m[3].read_rules(p)
 def test_21_firewall_rejects_port_zero(self):
  with tempfile.TemporaryDirectory() as d:
   p=csvtmp(d,'x.csv','protocol,port,source,action\nTCP,0,10.0.0.0/8,ALLOW\n')
   with self.assertRaises(ValueError):self.m[3].read_rules(p)

 # 22..25: IOC exact matching
 def test_22_ioc_domain_case_normalized(self):
  m=self.m[4]
  self.assertEqual('one.example.test',m.normalize('domain','ONE.EXAMPLE.TEST.'))
 def test_23_ioc_sha256_lowercase_normalized(self):
  m=self.m[4]
  self.assertEqual('a'*64,m.normalize('sha256','A'*64))
 def test_24_ioc_scoped_ipv6_is_rejected(self):
  with self.assertRaises(ValueError):self.m[4].normalize('ip','fe80::1%eth0')
 def test_25_ioc_sample_has_three_true_exact_matches(self):
  m=self.m[4]
  indicators=m.load_csv(ROOT/'samples/indicators.csv',('type','value'))
  events=m.load_csv(ROOT/'samples/ioc_events.csv',('timestamp',)+m.TYPES)
  self.assertEqual(3,len(m.correlate(indicators,events)))

 # 26..29: SHA-256 and baseline
 def test_26_hash_is_actual_sha256(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x';p.write_bytes(b'abc')
   self.assertEqual(hashlib.sha256(b'abc').hexdigest(),self.m[5].digest_file(p))
 def test_27_integrity_changed_added_removed(self):
  a={'a':'1','b':'2','c':'3'};b={'a':'4','b':'2','d':'5'}
  self.assertEqual([('a','MODIFIED'),('b','UNCHANGED'),('c','REMOVED'),('d','ADDED')],self.m[5].compare(a,b))
 def test_28_integrity_symlink_ignored(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'a.txt').write_text('abc')
   (root/'linked.txt').symlink_to(root/'a.txt')
   self.assertEqual({'a.txt'},set(self.m[5].snapshot(root)))
 def test_29_integrity_max_file_size_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'big';p.write_bytes(b'\0'*(5*1024*1024+1))
   with self.assertRaises(ValueError):self.m[5].digest_file(p)

 # 30..33: email parsing
 def test_30_mail_from_reply_mismatch_only_clue(self):
  result='\n'.join(self.m[6].analyze_email('From: a@example.test\nReply-To: b@outside.test\n'))
  self.assertIn('REVIEW:',result);self.assertIn('not proof',result)
 def test_31_mail_duplicate_from_not_trusted(self):
  result='\n'.join(self.m[6].analyze_email('From: a@example.test\nFrom: b@example.test\n'))
  self.assertIn('exactly one From',result)
 def test_32_mail_authentication_results_not_verified(self):
  result='\n'.join(self.m[6].analyze_email('From: a@example.test\nAuthentication-Results: evil.test; dkim=pass\n'))
  self.assertIn('cannot validate',result)
 def test_33_mail_invalid_domain_rejected(self):
  self.assertEqual('',self.m[6].domain_from_header('a@-bad.example.test'))

 # 34..36: throttle model
 def test_34_three_failures_lock_and_block_success(self):
  t=self.m[7].Throttle()
  for _ in range(2):self.assertIn('Recorded',t.attempt('FAIL'))
  self.assertIn('LOCKED',t.attempt('FAIL'))
  self.assertIn('BLOCKED',t.attempt('SUCCESS'))
 def test_35_throttle_exact_boundary_unblocks(self):
  t=self.m[7].Throttle()
  for _ in range(3):t.attempt('FAIL')
  t.advance(30)
  self.assertIn('Allowed',t.attempt('SUCCESS'))
 def test_36_throttle_bool_is_not_valid_time(self):
  t=self.m[7].Throttle()
  with self.assertRaises(ValueError):t.advance(True)

if __name__=='__main__':unittest.main()

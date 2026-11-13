"""42 focused source-and-manual checks built from reading each project by hand.

These are 42 independent questions, not claims of 42 full manual rereadings.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/'Python_GUI_サイバーセキュリティ7作品_全行詳細解説マニュアル.html'


def module(n):
    path=next((ROOT/'projects').glob(f'{n:02d}_*.py'))
    spec=importlib.util.spec_from_file_location('v7_audit_'+str(n),path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def sample_csv(text):
    f=tempfile.NamedTemporaryFile(mode='w',encoding='utf8',newline='',suffix='.csv',delete=False)
    f.write(text);f.close()
    return Path(f.name)


class CasesV7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m={i:module(i) for i in range(1,8)}
        cls.soup=BeautifulSoup(HTML.read_text(encoding='utf8'),'html.parser')

    # 01: authentication (5)
    def test_01_auth_sample_events(self):
        events=self.m[1].read_events(ROOT/'samples/auth_events.csv')
        self.assertEqual(6,len(events))
        self.assertEqual(3,self.m[1].summarize(events)[1]['198.51.100.8'])
    def test_02_auth_filter_does_not_recount(self):
        events=self.m[1].read_events(ROOT/'samples/auth_events.csv')
        visible,counts=self.m[1].summarize(events,'bob')
        self.assertEqual(2,len(visible))
        self.assertEqual(3,counts['198.51.100.8'])
    def test_03_auth_reject_unknown_status(self):
        p=sample_csv('timestamp,username,ip,status\nnow,a,192.0.2.1,UNKNOWN\n')
        try:
            with self.assertRaisesRegex(ValueError,'Status'): self.m[1].read_events(p)
        finally:p.unlink()
    def test_04_auth_timestamp_only_checked_for_empty(self):
        p=sample_csv('timestamp,username,ip,status\nnot-a-date,a,192.0.2.1,FAIL\n')
        try:self.assertEqual('not-a-date',self.m[1].read_events(p)[0]['timestamp'])
        finally:p.unlink()
    def test_05_auth_reject_duplicate_columns(self):
        p=sample_csv('timestamp,username,ip,ip,status\nnow,a,192.0.2.1,192.0.2.2,FAIL\n')
        try:
            with self.assertRaisesRegex(ValueError,'columns'):self.m[1].read_events(p)
        finally:p.unlink()

    # 02: headers (5)
    def test_06_header_repeated_cookie_preserved(self):
        h=self.m[2].parse_headers('Set-Cookie: x=a\nSet-Cookie: y=b\n')
        self.assertEqual(['x=a','y=b'],h['set-cookie'])
    def test_07_header_folding_rejected(self):
        with self.assertRaisesRegex(ValueError,'Invalid header'):
            self.m[2].parse_headers('X-Test: value\n bad-fold')
    def test_08_cookie_three_flags_seems_valid_only(self):
        h=self.m[2].parse_headers('Set-Cookie: sid=abc; Secure; HttpOnly; SameSite=Lax')
        self.assertTrue(any('SEEN: Cookie sid' in a for a in self.m[2].audit(h,True)))
    def test_09_cookie_none_without_secure_flagged(self):
        h=self.m[2].parse_headers('Set-Cookie: sid=abc; HttpOnly; SameSite=None')
        self.assertTrue(any('secure with SameSite=None' in a for a in self.m[2].audit(h,True)))
    def test_10_non_https_does_not_audit_hsts(self):
        self.assertTrue(any('HSTS assessment skipped' in a for a in self.m[2].audit({'content-type':['text/plain']},False)))

    # 03: firewall rule descriptions are heuristics (5)
    def test_11_firewall_public_ssh_candidate(self):
        self.assertEqual('REVIEW: broad sensitive access',self.m[3].assess(dict(source='0.0.0.0/0',port='22',action='ALLOW')))
    def test_12_firewall_hostbits_rejected(self):
        p=sample_csv('protocol,port,source,action\nTCP,22,10.0.0.1/24,ALLOW\n')
        try:
            with self.assertRaisesRegex(ValueError,'host bits'): self.m[3].read_rules(p)
        finally:p.unlink()
    def test_13_firewall_reject_unicode_digits(self):
        p=sample_csv('protocol,port,source,action\nTCP,٢٢,0.0.0.0/0,ALLOW\n')
        try:
            with self.assertRaises(ValueError):self.m[3].read_rules(p)
        finally:p.unlink()
    def test_14_firewall_any_short_circuit(self):
        self.assertEqual('REVIEW: broad sensitive access',self.m[3].assess(dict(source='::/0',port='any',action='ALLOW')))
    def test_15_firewall_rule_301_fails(self):
        header='protocol,port,source,action\n'
        p=sample_csv(header+'TCP,443,192.0.2.0/24,ALLOW\n'*301)
        try:
            with self.assertRaisesRegex(ValueError,'300'):self.m[3].read_rules(p)
        finally:p.unlink()

    # 04: domain, hash, exact matches (5)
    def test_16_ioc_domain_dot_and_case(self):
        self.assertEqual('example.test',self.m[4].normalize('domain','EXAMPLE.TEST.'))
    def test_17_ioc_multiple_terminal_dots(self):
        with self.assertRaises(ValueError):self.m[4].normalize('domain','example.test..')
    def test_18_ioc_sha64_and_lowercase(self):
        self.assertEqual('a'*64,self.m[4].normalize('sha256','A'*64))
    def test_19_ioc_empty_event_kind_skipped(self):
        indicators=[{'type':'ip','value':'192.0.2.1'}]
        events=[{'timestamp':'now','ip':'','domain':'','sha256':''}]
        self.assertEqual([],self.m[4].correlate(indicators,events))
    def test_20_ioc_three_sample_matches(self):
        mod=self.m[4]
        indicators=mod.load_csv(ROOT/'samples/indicators.csv',('type','value'))
        events=mod.load_csv(ROOT/'samples/ioc_events.csv',('timestamp',)+mod.TYPES)
        self.assertEqual(3,len(mod.correlate(indicators,events)))

    # 05: SHA-256 and imperfect snapshot semantics (5)
    def test_21_integrity_all_four_classes(self):
        self.assertEqual([('a','MODIFIED'),('b','UNCHANGED'),('c','ADDED'),('d','REMOVED')],self.m[5].compare({'a':'old','b':'same','d':'old'},{'a':'new','b':'same','c':'new'}))
    def test_22_integrity_real_sha256_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data';p.write_bytes(b'hello')
            self.assertEqual(hashlib.sha256(b'hello').hexdigest(),self.m[5].digest_file(p))
    def test_23_integrity_skips_link(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'real';p.write_bytes(b'hello')
            (Path(d)/'link').symlink_to(p)
            self.assertEqual(['real'],list(self.m[5].snapshot(d)))
    def test_24_integrity_five_megabyte_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'large';p.write_bytes(b'a'*(self.m[5].MAX_SIZE+1))
            with self.assertRaisesRegex(ValueError,'too large'):self.m[5].digest_file(p)
    def test_25_integrity_101_files(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(101):(Path(d)/f'{i:03}.txt').write_text('x')
            with self.assertRaisesRegex(ValueError,'100 files'):self.m[5].snapshot(d)

    # 06: email provides clues, not authentication (5)
    def test_26_mail_one_domain(self):
        self.assertEqual('example.test',self.m[6].domain_from_header('Alice <hello@example.test>'))
    def test_27_mail_duplicate_from_skip_comparison(self):
        text='From: a@example.test\nFrom: b@example.test\nReply-To: q@other.test\n'
        findings=self.m[6].analyze_email(text)
        self.assertTrue(any('Expected exactly one From' in a for a in findings))
    def test_28_mail_reply_domain_is_only_clue(self):
        findings=self.m[6].analyze_email('From: a@example.test\nReply-To: x@support.example.test\n')
        self.assertTrue(any('REVIEW:' in a for a in findings))
        self.assertTrue(any('not proof' in a for a in findings))
    def test_29_mail_auth_result_is_untrusted_text(self):
        findings=self.m[6].analyze_email('From: a@example.test\nAuthentication-Results: fake; spf=pass\n')
        self.assertTrue(any('cannot validate it' in a for a in findings))
    def test_30_mail_too_many_characters(self):
        with self.assertRaisesRegex(ValueError,'too long'):self.m[6].analyze_email('x'*(self.m[6].MAX_INPUT+1))

    # 07: clock and lockout model (5)
    def test_31_throttle_lock_after_three(self):
        obj=self.m[7].Throttle();[obj.attempt('FAIL') for _ in range(3)]
        self.assertEqual(30,obj.lock_until)
    def test_32_throttle_block_success_in_lock(self):
        obj=self.m[7].Throttle();[obj.attempt('FAIL') for _ in range(3)]
        self.assertIn('BLOCKED',obj.attempt('SUCCESS'))
    def test_33_throttle_unlock_at_exact_boundary(self):
        obj=self.m[7].Throttle();[obj.attempt('FAIL') for _ in range(3)]
        obj.advance(30)
        self.assertIn('Allowed',obj.attempt('SUCCESS'))
    def test_34_throttle_age_60_seconds_expires(self):
        obj=self.m[7].Throttle();obj.attempt('FAIL');obj.advance(60)
        self.assertEqual([],obj.fail_times)
    def test_35_throttle_boolean_time_rejected(self):
        with self.assertRaises(ValueError):self.m[7].Throttle().advance(True)

    # 7 explicit checks of correct syntax in actual annotations, not mere source presence.
    def check_row_piece(self,n,line,word,expected):
        r=self.soup.select_one(f'#v6-line-{n:02d}-{line}')
        self.assertIsNotNone(r)
        matches=[p.find('span').get_text() for p in r.select('span.piece') if p.find('code') and p.find('code').get_text()==word]
        self.assertTrue(any(expected in text for text in matches),(n,line,word,matches))
    def test_36_manual_default_parameter_not_assignment(self):
        self.check_row_piece(1,42,'=','省略時の値')
    def test_37_manual_keyword_argument_not_assignment(self):
        self.check_row_piece(1,57,'=','キーワード引数')
    def test_38_manual_raise_from_cause_not_import(self):
        self.check_row_piece(1,35,'from','原因の例外')
    def test_39_manual_except_as_variable_not_alias(self):
        self.check_row_piece(1,34,'as','例外を指定した変数名')
    def test_40_manual_set_function_not_gui_setter(self):
        self.check_row_piece(1,22,'set','集合set')
    def test_41_manual_union_keys_not_bitwise_flag(self):
        self.check_row_piece(5,59,'|','和集合')
    def test_42_manual_all_seven_deep_guides(self):
        for n in range(1,8):
            el=self.soup.select_one(f'#v7-precision-{n:02d}')
            self.assertIsNotNone(el)
            self.assertEqual(6,len(el.select('tbody tr')))
        self.assertIsNotNone(self.soup.select_one('#v7-context-grammar'))

if __name__=='__main__':unittest.main()

import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from verovo_healthcheck.response_audit import audit
from verovo_healthcheck.cli import main

class TestResponseAudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def row(self, id='secret-id', output=7):
        return dict(type='assistant',message=dict(id=id,model='m',content='PRIVATE',usage=dict(input_tokens=10,output_tokens=output,cache_read_input_tokens=3,cache_creation_input_tokens=0)))
    def file(self,name,rows):
        path=self.root/name
        path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
        return str(path)
    def test_repeated_response_across_files_has_no_billing_total(self):
        r=audit([self.file('a.jsonl',[self.row()]),self.file('b.jsonl',[self.row()])])
        self.assertEqual(r['repeated_across_files'],1)
        self.assertEqual(r['responses'][0]['state'],'OBSERVED')
        self.assertIsNone(r['session_token_total'])
        self.assertNotIn('PRIVATE',json.dumps(r))
        self.assertNotIn('secret-id',json.dumps(r))
    def test_conflicting_snapshots_do_not_choose_a_total(self):
        r=audit([self.file('a.jsonl',[self.row(),self.row(output=8)])])
        self.assertEqual(r['conflicting_groups'],1)
        self.assertIsNone(r['invoice_total'])
    def test_missing_identity_not_grouped(self):
        r=audit([self.file('a.jsonl',[self.row(id=None),self.row(id='')])])
        self.assertEqual(r['counts']['missing_response_id'],2)
        self.assertEqual(r['response_groups'],0)
    def test_missing_cache_not_zero(self):
        row=self.row();del row['message']['usage']['cache_creation_input_tokens']
        self.assertEqual(audit([self.file('a.jsonl',[row])])['incomplete_groups'],1)
    def test_boolean_or_negative_usage_not_valid(self):
        self.assertEqual(audit([self.file('a.jsonl',[self.row(output=True),self.row(id='other',output=-1)])])['incomplete_groups'],2)
    def test_same_file_twice_not_cross_file_duplicate(self):
        p=self.file('a.jsonl',[self.row()]);r=audit([p,p])
        self.assertEqual(r['repeated_across_files'],0)
        self.assertEqual(r['counts']['assistant_rows'],1)
    def test_bad_rows_are_disclosed(self):
        p=self.root/'a.jsonl';p.write_text('{bad}\n[]\n'+json.dumps(self.row())+'\n')
        self.assertEqual(audit([str(p)])['counts']['invalid_rows'],2)
    def test_conflicting_request_identity(self):
        a=self.row();b=self.row();a['requestId']='a';b['requestId']='b'
        self.assertEqual(audit([self.file('a.jsonl',[a,b])])['conflicting_groups'],1)
    def test_output_cannot_overwrite_input(self):
        p=self.file('a.jsonl',[self.row()]);before=Path(p).read_bytes()
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            rc=main(['response-audit',p,'--json',p])
        self.assertEqual(rc,2);self.assertEqual(Path(p).read_bytes(),before)
    def test_missing_input_is_error(self):
        with self.assertRaises(OSError):audit([str(self.root/'missing')])

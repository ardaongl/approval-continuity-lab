import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from approval_continuity_lab.report import serialize
from approval_continuity_lab.scenarios import dispatch
from tests.support.base import Case, asset, FIXTURES, AGENT, REVIEWER, rows

FIELDS=set('schema_version command mode outcome code proposal_id approval_id execution_id status observed_at_ms authorized_at_ms replayed effect_status details data'.split())


class DeterministicReports(Case):
    def test_every_scenario_twice_in_fresh_processes_json_and_text(self):
        command=[sys.executable,'-I','-B','-m','approval_continuity_lab','scenario','run','all']
        for format in ('json','text'):
            outputs=[]
            for i in range(2):
                directory=self.path.parent/('repeat-'+format+str(i));directory.mkdir()
                p=subprocess.run(command+['--format',format],cwd=directory,capture_output=True,timeout=30)
                self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,b'');self.assertEqual(list(directory.iterdir()),[])
                self.assertTrue(p.stdout.endswith(b'\n'));self.assertNotIn(b'\r',p.stdout);self.assertLessEqual(len(p.stdout),1048576)
                outputs.append(p.stdout)
            self.assertEqual(*outputs)
            from tests.support.evidence import save
            save('interface-'+format,{'first':outputs[0].decode(),'second':outputs[1].decode(),'byte_identical':True})
            value=json.loads(outputs[0] if format=='json' else outputs[0].split(b'DATA: ',1)[1])
            if format=='text':value={'data':value}
            else:self.assertEqual(set(value),FIELDS)
            scenarios=value['data']['scenarios'];self.assertEqual([s['scenario_id'] for s in scenarios],['D%02d'%i for i in range(1,15)])
            for s in scenarios:
                self.assertTrue(s['verified']);self.assertEqual(set(s),{'scenario_id','classification','verified','observations','explanation'})
                for observation in s['observations']:self.assertEqual(set(observation),{'step','code','status','effect_count','service_revision'})

    def test_api_cli_frozen_execution_and_review_text(self):
        self.seed(False)
        p=subprocess.run([sys.executable,'-I','-B','-m','approval_continuity_lab','review','--db',str(self.path),'--actor','rev_a','--now-ms','1400','--proposal-id','p1','--format','text'],capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr);self.assertTrue(p.stdout.endswith((FIXTURES/'review-suffix.golden.txt').read_bytes()))
        self.clock.now=1500;self.code(self.lab.decide(asset('decision-input.json'),REVIEWER));self.clock.now=1600
        p=subprocess.run([str(Path(sys.executable).parent/'acl'),'execute','--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600','--input',str(FIXTURES/'execution-input.json')],capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stdout,(FIXTURES/'d01-report.golden.json').read_bytes())

    def test_b1_cli_literal_json_text_and_scalar_distinction(self):
        from approval_continuity_lab import Lab
        full=[]
        for i,(reason,literal) in enumerate([('é',br'"\u00e9"'),('e\u0301',br'"e\u0301"'),('😀',br'"\ud83d\ude00"'),('İzin',br'"\u0130zin"'),('A\n\x1b',br'"A\n\u001b"')]):
            self.path=self.path.with_name(f'cli-reason{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed(False);self.clock.now=1500
            body=asset('decision-input.json');body['reason']=reason
            input_file=self.path.with_suffix('.json');input_file.write_text(json.dumps(body,ensure_ascii=False))
            common=['decide','--db',str(self.path),'--actor','rev_a','--now-ms','1500','--input',str(input_file)]
            p=subprocess.run([sys.executable,'-I','-B','-m','approval_continuity_lab',*common],capture_output=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            expected=(FIXTURES/'decision.expected.json').read_bytes().rstrip(b'\n').replace(b'"Reviewed exact manifest"',literal)
            self.assertIn(b'"reason":'+literal,p.stdout);self.assertEqual(rows(self.path,'decisions')[0]['canonical_decision'].encode(),expected)
            value=json.loads(p.stdout);self.assertEqual(value['data']['decision_digest'],hashlib.sha256(b'ACL/v1/decision\0'+expected).hexdigest())
            # Retry using escaped JSON, including a valid surrogate pair for
            # the supplementary reason: decoded content must remain identical.
            input_file.write_text(json.dumps(body,ensure_ascii=True))
            text=subprocess.run([sys.executable,'-I','-B','-m','approval_continuity_lab',*common,'--format','text'],capture_output=True,timeout=15)
            self.assertEqual(text.returncode,0,text.stderr);self.assertIn(b'"reason":'+literal,text.stdout);self.assertNotIn(b'\x1b',text.stdout)
            full.append(expected)
        self.assertNotEqual(full[0],full[1])

    def test_scenario_failure_stops_without_claiming_later_success(self):
        def fail(id,directory):raise RuntimeError('coordinator fault')
        with patch('approval_continuity_lab.scenarios.experiment',fail):r=dispatch('scenario-run','all')
        self.assertEqual(r['code'],'SCENARIO_FAILED');self.assertEqual(len(r['data']['scenarios']),1);self.assertFalse(r['data']['scenarios'][0]['verified'])

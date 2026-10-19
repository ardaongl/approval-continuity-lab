"""Additional resource/precedence invariants referenced by AC-03/11/12/18."""
import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
from approval_continuity_lab import Lab
from approval_continuity_lab.models import MAX_INT
from approval_continuity_lab.report import serialize, report
from approval_continuity_lab.models import Failure
from tests.support.base import Case, Clock, asset, snapshot, rows, AGENT, REVIEWER, OPERATOR, A, C, FIXTURES


class BoundaryInvariants(Case):
    def test_raw_cli_decode_failures_preserve_all_rows(self):
        self.seed();before=snapshot(self.path)
        raw_cases=[(b'{"a":1,"a":1}',2),(b'{"a":{"b":1,"b":2}}',2),(b'"\\ud800"',2),(b'"\xed\xa0\x80"',2),(b'\xff',2),(b'\xef\xbb\xbf{}',2),(b'1.0',2),(b'1e0',2),(b'NaN',2),(b'Infinity',2),(b'9007199254740992',2),(b'['*17+b'0'+b']'*17,2),(b' '*65537,2)]
        args=[sys.executable,'-I','-B','-m','approval_continuity_lab','decide','--db',str(self.path),'--actor','rev_a','--now-ms','2000','--input','-']
        for raw,expected in raw_cases:
            with self.subTest(raw=raw[:30]):
                p=subprocess.run(args,input=raw,capture_output=True,timeout=15)
                self.assertEqual(p.returncode,expected,p.stderr);self.assertIn(json.loads(p.stdout)['code'],('INPUT_INVALID','INPUT_LIMIT'));self.assertEqual(snapshot(self.path),before)

    def test_config_row_boundary_and_real_raw_utf8_size(self):
        cfg=asset('base-config.json')
        # 128 UTF-8 bytes of supplementary scalars need 384 canonical ASCII
        # bytes. The wire size, rather than C's escape size, owns input limit.
        cfg['services']=[dict(cfg['services'][0],service_id='s%d'%i,display_name='😀'*32) for i in range(160)]
        raw=json.dumps(cfg,ensure_ascii=False,separators=(',',':')).encode()
        self.assertLessEqual(len(raw),65536)
        self.assertGreater(len(json.dumps(cfg,ensure_ascii=True,separators=(',',':')).encode()),65536)
        from approval_continuity_lab.validation import decode
        self.code(self.lab.initialize(decode(raw),OPERATOR));self.assertEqual(len(rows(self.path,'services')),160)
        for count,code in [(256,'OK'),(257,'INPUT_INVALID')]:
            path=self.path.with_name('rows%d.sqlite'%count);lab=Lab.open(path,self.clock)
            cfg=asset('base-config.json');cfg['actors']=[{'actor_id':'op','role':'operator'}]+[{'actor_id':'a%d'%i,'role':'agent'} for i in range(count-1)];cfg['contexts']=[];cfg['eligibility']=[]
            self.code(lab.initialize(cfg,OPERATOR),code)
            if code!='OK':self.assertFalse(path.exists())

    def test_revision_limits_and_same_value_admin_bumps(self):
        cfg=asset('base-config.json');cfg['services'][0]['revision']=MAX_INT
        self.seed(False,config=cfg)
        # Build input from independently altered authored P/R fields.
        p=asset('proposal.expected.json');p['expected_target_revision']=MAX_INT
        def h(domain,value):return hashlib.sha256(b'ACL/v1/'+domain.encode()+b'\0'+json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        review={'kind':'approval-review-v1','proposal':p}
        d=asset('decision-input.json');d['review_digest']=h('review',review)
        self.clock.now=1500;self.code(self.lab.decide(d,REVIEWER))
        body=asset('execution-input.json');body['intent'].update(binding=p,proposal_digest=h('proposal',p),review_digest=h('review',review))
        self.clock.now=1600;self.execute(body,code='LIMIT_EXCEEDED')
        self.assertEqual(rows(self.path,'services')[0]['revision'],MAX_INT);self.assertEqual(rows(self.path,'executions'),[])
        self.code(self.lab.admin_update(dict(schema_version=1,kind='service',id='svc1',expected_revision=MAX_INT,changes={'artifact_digest':C}),OPERATOR),'LIMIT_EXCEEDED')
        self.path=self.path.with_name('same-value.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
        self.admin(changes={'artifact_digest':A});self.assertEqual(rows(self.path,'services')[0]['revision'],2);self.clock.now=1600
        self.execute(code='TARGET_REVISION_CHANGED')

    def test_thousand_proposal_limit_before_protected_mutation(self):
        self.seed();base=rows(self.path,'proposals')[0]
        def c(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
        def h(d,x):return hashlib.sha256(('ACL/v1/'+d+'\0'+c(x)).encode()).hexdigest()
        with sqlite3.connect(self.path) as connection:
            connection.execute('PRAGMA foreign_keys=ON')
            for n in range(2,1001):
                p=asset('proposal.expected.json');p.update(proposal_id='p%d'%n,request_id='q%d'%n)
                sub=asset('submission.json');sub.update(proposal_id=p['proposal_id'],request_id=p['request_id'])
                review={'kind':'approval-review-v1','proposal':p}
                row=dict(base,proposal_id=p['proposal_id'],request_id=p['request_id'],canonical_proposal=c(p),proposal_digest=h('proposal',p),canonical_review=c(review),review_digest=h('review',review),submission_json=c(sub),status='pending',status_at_ms=1000)
                connection.execute('INSERT INTO proposals('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
                connection.execute('INSERT INTO transitions VALUES(?,1,NULL,\'pending\',NULL,1000)',(p['proposal_id'],))
        sub=asset('submission.json');sub.update(proposal_id='p1001',request_id='q1001')
        self.clock.now=1600;self.code(self.lab.propose(sub,AGENT),'LIMIT_EXCEEDED')
        self.assertEqual(len(rows(self.path,'proposals')),1000);self.assertEqual(rows(self.path,'services')[0]['revision'],1);self.assertEqual(rows(self.path,'executions'),[])

    def test_admin_selected_record_precedes_time_and_denial_maintenance(self):
        self.seed();before=snapshot(self.path);self.clock.now=0
        r=self.lab.admin_update(dict(schema_version=1,kind='service',id='missing',expected_revision=1,changes={'artifact_digest':C}),OPERATOR)
        self.code(r,'NOT_FOUND');self.assertEqual(snapshot(self.path),before)
        self.clock.now=1700;body=asset('execution-input.json');body['intent']['review_digest']='0'*64
        self.execute(body,code='BINDING_MISMATCH');self.assertEqual(rows(self.path,'meta')[0]['observed_time_floor_ms'],1700)
        self.unchanged_effect()

    def test_revoke_all_terminal_states_and_history_ownership(self):
        for i,state in enumerate(('rejected','expired','superseded','consumed')):
            self.path=self.path.with_name('terminal%d.sqlite'%i);self.lab=Lab.open(self.path,self.clock);self.seed(False)
            body=asset('decision-input.json')
            if state=='rejected':body['decision']='reject'
            self.clock.now=1500;self.code(self.lab.decide(body,REVIEWER));self.clock.now=1600
            if state=='expired':self.clock.now=2500;self.execute(code='GRANT_EXPIRED')
            elif state=='superseded':self.admin();self.execute(code='TARGET_REVISION_CHANGED')
            elif state=='consumed':self.execute()
            self.code(self.lab.revoke({'schema_version':1,'proposal_id':'p1'},REVIEWER),'TOO_LATE' if state=='consumed' else 'INVALID_STATE')
            if state=='consumed':
                self.code(self.lab.inspect('execution','x1',{'actor_id':'req_b','context_id':'c2'}),'CALLER_MISMATCH')

    def test_report_bound_is_enforced(self):
        value=report('invalid',data={'large':'x'*1048576})
        with self.assertRaises(Failure) as e:serialize(value)
        self.assertEqual(e.exception.code,'INTERNAL_ERROR')

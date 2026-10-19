from approval_continuity_lab.canonical import digest
from approval_continuity_lab.report import serialize
from tests.support.base import Case, asset, rows, AGENT, REVIEWER, A, C, FIXTURES


class TargetDrift(Case):
    def test_both_target_writer_process_orderings(self):
        from approval_continuity_lab import Lab
        from approval_continuity_lab.processes import Worker
        from tests.support.base import snapshot
        from tests.support.evidence import save
        for i,(first,second,code) in enumerate([('target-before','execute-a','TARGET_REVISION_CHANGED'),('execute-a','target-after','REVISION_CONFLICT')]):
            self.path=self.path.with_name(f'targetrace{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            with Worker(self.path,first) as a,Worker(self.path,second) as b:
                a.reach('after_begin');b.reach('before_begin');b.release();self.code(a.finish());self.code(b.finish(),code)
                state=snapshot(self.path);self.assertEqual(state['services'][0]['revision'],2)
                self.assertEqual(len(state['executions']),i)
                save(f'd08-race-{i}',{'a':a.events,'b':b.events,'sql':state})

    def test_drift_golden_and_aba_terminal(self):
        self.seed();self.admin();self.clock.now=1600
        r=self.execute(code='TARGET_REVISION_CHANGED')
        self.assertEqual(serialize(r),(FIXTURES/'d08-report.golden.json').read_bytes())
        self.unchanged_effect('superseded',C,2)
        self.admin(changes={'artifact_digest':A},expected=2,now=1700);self.clock.now=1800
        self.execute(code='TARGET_REVISION_CHANGED');self.unchanged_effect('superseded',A,3)

    def test_aba_before_first_reconciliation(self):
        self.seed();self.admin();self.admin(changes={'artifact_digest':A},expected=2,now=1575);self.clock.now=1600
        self.execute(code='TARGET_REVISION_CHANGED');self.unchanged_effect('superseded',A,3)

    def test_fresh_replacement_and_old_grant_stays_unusable(self):
        self.seed();self.admin();self.clock.now=1600;self.execute(code='TARGET_REVISION_CHANGED')
        sub=asset('submission.json');sub.update(proposal_id='p2',request_id='q2',replaces_proposal_id='p1',pending_deadline_ms=3000)
        self.clock.now=1700;r=self.code(self.lab.propose(sub,AGENT));self.assertEqual(rows(self.path,'proposals')[0]['replacement_id'],'p2')
        d=asset('decision-input.json');d.update(approval_id='a2',proposal_id='p2',review_digest=r['data']['review_digest'])
        self.clock.now=1800;self.code(self.lab.decide(d,REVIEWER))
        body={'schema_version':1,'execution_id':'x2','approval_id':'a2','intent':{'proposal_id':'p2','proposal_digest':r['data']['proposal_digest'],'review_digest':r['data']['review_digest'],'binding':r['data']['proposal']}}
        self.clock.now=1900;self.execute(body);self.assertEqual(rows(self.path,'services')[0]['revision'],3)
        self.execute(code='TARGET_REVISION_CHANGED')

    def test_same_display_name_is_not_same_identity(self):
        self.seed();body=asset('execution-input.json');body['intent']['binding']['target_service_id']='svc2'
        self.execute(body,code='BINDING_MISMATCH');self.unchanged_effect()
        self.assertEqual(rows(self.path,'services')[1]['revision'],1)

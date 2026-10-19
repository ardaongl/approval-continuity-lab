from tests.support.base import Case, asset, rows, snapshot, AGENT, REVIEWER


class Idempotency(Case):
    def test_history_ignores_current_drift_expiry_and_backwards_clock(self):
        self.seed();first=self.execute();stored=rows(self.path,'executions')[0]['result_json']
        for kind,id in [('service','svc1'),('context','c1'),('policy','t1'),('eligibility','t1')]:
            self.admin(kind,id,expected=2 if kind=='service' else 1,now=1700)
        current=snapshot(self.path);calls=self.clock.calls
        for now in (5000,0):
            self.clock.now=now;r=self.execute();self.assertTrue(r['replayed']);self.assertIsNone(r['observed_at_ms']);self.assertEqual(r['data']['result'],first['data']['result'])
            self.assertEqual(rows(self.path,'executions')[0]['result_json'],stored);self.assertEqual(snapshot(self.path),current)
        self.assertEqual(self.clock.calls,calls)
        self.clock.now=1800;self.code(self.lab.revoke({'schema_version':1,'proposal_id':'p1'},REVIEWER),'TOO_LATE')

    def test_conflicting_execution_and_different_id(self):
        self.seed();self.execute()
        for mutate in ('artifact','approval'):
            body=asset('execution-input.json')
            if mutate=='artifact':body['intent']['binding']['plan']['steps'][0]['arguments']['artifact_digest']='sha256:'+'c'*64
            else:body['intent']['proposal_id']='p2'
            self.execute(body,code='IDEMPOTENCY_CONFLICT')
        body=asset('execution-input.json');body['execution_id']='x2';self.execute(body,code='APPROVAL_CONSUMED')
        self.assertEqual(len(rows(self.path,'executions')),1);self.assertEqual(rows(self.path,'services')[0]['revision'],2)
        self.execute(caller={'actor_id':'req_b','context_id':'c2'},code='CALLER_MISMATCH')

    def test_propose_and_decide_key_reuse(self):
        self.seed();initial=snapshot(self.path);self.clock.now=0
        self.assertTrue(self.code(self.lab.propose(asset('submission.json'),AGENT))['replayed'])
        self.assertTrue(self.code(self.lab.decide(asset('decision-input.json'),REVIEWER))['replayed'])
        self.assertEqual(snapshot(self.path),initial)
        for field in ('proposal_id','request_id','description'):
            body=asset('submission.json');body[field]+='x';self.code(self.lab.propose(body,AGENT),'IDEMPOTENCY_CONFLICT')
        body=asset('decision-input.json');body['approval_id']='a2';self.code(self.lab.decide(body,REVIEWER),'INVALID_STATE')
        self.assertEqual(snapshot(self.path),initial)

    def test_denied_attempt_does_not_reserve_id(self):
        self.seed();body=asset('execution-input.json');body['intent']['review_digest']='0'*64
        self.execute(body,code='BINDING_MISMATCH');self.assertEqual(rows(self.path,'executions'),[]);self.execute()

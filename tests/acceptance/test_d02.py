import copy
from tests.support.base import Case, asset, rows, snapshot, AGENT, A


class SubmittedMutations(Case):
    def test_each_well_typed_binding_field_and_correct_retry(self):
        self.seed()
        p=asset('proposal.expected.json')
        immutable=rows(self.path,'proposals')[0]['canonical_proposal'];decision=rows(self.path,'decisions')
        variants=[]
        for key,value in p.items():
            if key in ('schema_version','tool_id','plan'):continue
            new = value+1 if type(value) is int else ('p0' if value is None else ('0'*64 if key.endswith('_digest') and key!='prior_artifact_digest' else A if key=='prior_artifact_digest' else value+'x'))
            if key=='prior_artifact_digest':new='sha256:'+'c'*64
            variants.append(([key],new))
        variants += [(['plan','revision'],2),(['plan','steps',0,'step_id'],'s2'),(['plan','steps',0,'arguments','artifact_digest'],'sha256:'+'c'*64),(['plan','steps',0,'arguments','service_id'],'svc2')]
        for path,value in variants:
            body=asset('execution-input.json');target=body['intent']['binding']
            for k in path[:-1]:target=target[k]
            target[path[-1]]=value
            with self.subTest(path=path):
                r=self.execute(body,code='BINDING_MISMATCH')
                self.assertEqual([d['path'] for d in r['details']],['/binding/'+ '/'.join(map(str,path))])
                self.unchanged_effect();self.assertEqual(rows(self.path,'decisions'),decision)
                self.assertEqual(rows(self.path,'proposals')[0]['canonical_proposal'],immutable)
        for key in ('proposal_id','proposal_digest','review_digest'):
            body=asset('execution-input.json');body['intent'][key]='p2' if key=='proposal_id' else '0'*64
            self.execute(body,code='BINDING_MISMATCH')
        self.execute()

    def test_wrong_caller_cannot_observe_or_mutate(self):
        self.seed();before=snapshot(self.path)
        for caller in ({'actor_id':'req_b','context_id':'c2'},{'actor_id':'req_a','context_id':'c3'}):
            for action in (lambda:self.lab.execute(asset('execution-input.json'),caller),lambda:self.lab.inspect('execution','missing',caller),lambda:self.lab.review('p1',caller)):
                r=action();self.assertIn(r['code'],('CALLER_MISMATCH','NOT_FOUND'))
                self.assertIsNone(r['data']);self.assertIsNone(r['proposal_id'])
            self.assertEqual(snapshot(self.path),before)

    def test_extra_or_reordered_two_steps_reject_before_state(self):
        self.seed();before=snapshot(self.path)
        for reverse in (False,True):
            body=asset('execution-input.json');steps=body['intent']['binding']['plan']['steps'];other=copy.deepcopy(steps[0]);other['step_id']='s2';steps.append(other)
            if reverse:steps.reverse()
            self.execute(body,code='INPUT_INVALID')
            self.assertEqual(snapshot(self.path),before)

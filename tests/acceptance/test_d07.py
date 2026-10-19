from approval_continuity_lab import Lab
from approval_continuity_lab.processes import Worker
from tests.support.base import Case, REVIEWER, AGENT, rows, snapshot
from tests.support.evidence import save


class Revocation(Case):
    def test_both_serialized_process_orderings(self):
        for i,(first,second,expected,status,count) in enumerate([('revoke-before','execute-a','APPROVAL_REVOKED','revoked',0),('execute-a','revoke-after','TOO_LATE','consumed',1)]):
            self.path=self.path.with_name(f'revoke{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            with Worker(self.path,first) as a,Worker(self.path,second) as b:
                a.reach('after_begin');b.reach('before_begin');b.release()
                a.reach('before_commit');self.assertEqual(len(rows(self.path,'executions')),0)
                self.code(a.finish());self.code(b.finish(),expected)
                state=snapshot(self.path);self.assertEqual(state['proposals'][0]['status'],status);self.assertEqual(len(state['executions']),count)
                save(f'd07-{i}',{'a':a.events,'b':b.events,'sql':state})

    def test_pending_repeated_and_other_terminal_states(self):
        from tests.support.base import asset
        self.seed(False);body={'schema_version':1,'proposal_id':'p1'}
        self.code(self.lab.revoke(body,REVIEWER),'APPROVAL_PENDING')
        self.execute(code='NOT_FOUND')
        self.code(self.lab.revoke(body,AGENT),'ROLE_FORBIDDEN')
        self.code(self.lab.decide(asset('decision-input.json'),REVIEWER))
        self.code(self.lab.revoke(body,REVIEWER));before=len(rows(self.path,'transitions'))
        self.assertFalse(self.code(self.lab.revoke(body,REVIEWER))['data']['changed']);self.assertEqual(len(rows(self.path,'transitions')),before)

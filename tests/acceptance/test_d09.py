from approval_continuity_lab import Lab
from tests.support.base import Case, asset, rows, Clock, AGENT, REVIEWER, OPERATOR, C


class AuthoritativeDrift(Case):
    def test_each_revision_and_withdrawal(self):
        for kind,id,code in [('tool','deploy_artifact','TOOL_CHANGED'),('context','c1','CONTEXT_CHANGED'),('policy','t1','POLICY_CHANGED'),('eligibility','t1','REVIEWER_CHANGED')]:
            with self.subTest(kind=kind):
                self.path=self.path.with_name(kind+'.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
                self.admin(kind,id);self.clock.now=1600;self.execute(code=code);self.unchanged_effect('superseded')
                restored={'policy':{'enabled':True},'eligibility':{'allowed':True},'context':{'executor_id':'ex1'},'tool':{}}[kind]
                self.admin(kind,id,changes=restored,expected=2,now=1700);self.clock.now=1800;self.execute(code=code)

    def test_ordering_expiry_before_all_drift_and_drift_before_intent(self):
        self.seed()
        for kind,id in [('service','svc1'),('eligibility','t1'),('policy','t1'),('tool','deploy_artifact'),('context','c1')]:self.admin(kind,id)
        self.clock.now=1600;body=asset('execution-input.json');body['intent']['review_digest']='0'*64
        self.execute(body,code='CONTEXT_CHANGED');self.unchanged_effect('superseded',C,2)
        self.path=self.path.with_name('expired.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed();self.admin('context','c1');self.clock.now=2500
        self.execute(code='GRANT_EXPIRED');self.unchanged_effect('expired')

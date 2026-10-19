from approval_continuity_lab import Lab
from approval_continuity_lab.models import MAX_INT
from tests.support.base import Case, asset, Clock, AGENT, REVIEWER, OPERATOR, rows, snapshot


class TimeAndExpiry(Case):
    def fixture(self, name, approved):
        path=self.path.with_name(name+'.sqlite');clock=Clock();lab=Lab.open(path,clock)
        self.code(lab.initialize(asset('base-config.json'),OPERATOR));self.code(lab.propose(asset('submission.json'),AGENT))
        if approved:
            clock.now=1500;self.code(lab.decide(asset('decision-input.json'),REVIEWER))
        return path,clock,lab

    def test_exact_pending_and_grant_boundaries(self):
        for approved,times in [(False,(1999,2000,2001)),(True,(2499,2500,2501))]:
            for n in times:
                with self.subTest(approved=approved,time=n):
                    path,clock,lab=self.fixture(str(n),approved);clock.now=n
                    r=lab.execute(asset('execution-input.json'),AGENT) if approved else lab.decide(asset('decision-input.json'),REVIEWER)
                    expected='OK' if n==times[0] else 'GRANT_EXPIRED' if approved else 'PENDING_EXPIRED'
                    self.code(r,expected)
                    self.assertEqual(rows(path,'proposals')[0]['status'],('consumed' if approved else 'approved') if expected=='OK' else 'expired')
                    if expected!='OK':self.assertEqual(rows(path,'executions'),[])

    def test_floor_restart_and_equality(self):
        self.seed();self.clock.now=2400;self.code(self.lab.inspect('proposal','p1',AGENT));old=snapshot(self.path)
        for restart in (False,True):
            self.clock.now=2399;lab=Lab.open(self.path,self.clock) if restart else self.lab
            self.code(lab.execute(asset('execution-input.json'),AGENT),'CLOCK_REGRESSION')
            self.assertEqual(snapshot(self.path),old)
        self.clock.now=2400;self.execute()

    def test_late_approval_and_fixed_retry(self):
        self.seed(False);self.clock.now=1999
        r=self.code(self.lab.decide(asset('decision-input.json'),REVIEWER))
        self.assertEqual(r['data']['decision']['expires_at_ms'],2999)
        self.clock.now=0;self.code(self.lab.decide(asset('decision-input.json'),REVIEWER))
        self.assertEqual(rows(self.path,'decisions')[0]['expires_at_ms'],2999)

    def test_overflow_and_no_clock_read_on_historical_retry(self):
        sub=asset('submission.json');sub['pending_deadline_ms']=MAX_INT
        self.clock.now=MAX_INT-1000;self.code(self.lab.initialize(asset('base-config.json'),OPERATOR));self.code(self.lab.propose(sub,AGENT))
        self.clock.now=MAX_INT-500
        import hashlib,json
        expected=asset('review.expected.json');expected['proposal']['created_at_ms']=MAX_INT-1000;expected['proposal']['pending_deadline_ms']=MAX_INT
        body=asset('decision-input.json');body['review_digest']=hashlib.sha256(b'ACL/v1/review\0'+json.dumps(expected,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        self.code(self.lab.decide(body,REVIEWER),'LIMIT_EXCEEDED')
        self.assertEqual(rows(self.path,'decisions'),[])
        self.assertEqual(rows(self.path,'proposals')[0]['status'],'pending')

    def test_expired_never_revives(self):
        self.seed();self.clock.now=2500;self.execute(code='GRANT_EXPIRED')
        before=snapshot(self.path);self.clock.now=2499;self.execute(code='CLOCK_REGRESSION');self.assertEqual(snapshot(self.path),before)
        self.clock.now=2501;self.execute(code='GRANT_EXPIRED');self.unchanged_effect('expired')

    def test_check_time_is_not_commit_wall_time(self):
        self.seed();self.clock.now=2499
        class Observer:
            def reached(_,point):
                if point=='before_commit':self.clock.now=2501
        lab=Lab.open(self.path,self.clock,Observer())
        r=self.code(lab.execute(asset('execution-input.json'),AGENT))
        self.assertEqual(r['authorized_at_ms'],2499);self.assertEqual(rows(self.path,'executions')[0]['authorized_at_ms'],2499)

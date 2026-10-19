from approval_continuity_lab.report import serialize
from tests.support.base import Case, FIXTURES, rows, B, A


class ApprovedExecution(Case):
    def test_exact_once_and_frozen_report(self):
        self.seed()
        result=self.execute()
        self.assertEqual(serialize(result),(FIXTURES/'d01-report.golden.json').read_bytes())
        services=rows(self.path,'services')
        self.assertEqual([(x['artifact_digest'],x['revision']) for x in services],[(B,2),(A,1),(A,1)])
        executions=rows(self.path,'executions')
        self.assertEqual(len(executions),1)
        self.assertEqual((executions[0]['before_revision'],executions[0]['after_revision'],executions[0]['authorized_at_ms']),(1,2,1600))
        self.assertEqual(rows(self.path,'decisions')[0]['expires_at_ms'],2500)
        self.assertEqual(rows(self.path,'meta')[0]['observed_time_floor_ms'],1600)
        self.assertEqual([h['to_status'] for h in rows(self.path,'transitions')],['pending','approved','consumed'])

from approval_continuity_lab import Lab
from approval_continuity_lab.processes import Worker
from tests.support.base import Case, rows, snapshot, AGENT, asset, A, B
from tests.support.evidence import save


class CrashRecovery(Case):
    def test_real_sigkill_before_and_after_commit(self):
        for i,point in enumerate(('before_commit','after_commit_before_response')):
            self.path=self.path.with_name(f'crash{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            with Worker(self.path,'execute-same') as worker:
                worker.reach(point)
                held=snapshot(self.path)
                self.assertEqual(held['services'][0]['artifact_digest'],A if i==0 else B)
                self.assertEqual(held['proposals'][0]['status'],'approved' if i==0 else 'consumed')
                self.assertEqual(len(held['executions']),i)
                self.assertEqual(held['meta'][0]['observed_time_floor_ms'],1500 if i==0 else 1600)
                worker.kill()
                reopened=snapshot(self.path);self.assertEqual(reopened,held)
                self.lab=Lab.open(self.path,self.clock)
                r=self.execute();self.assertEqual(r['replayed'],bool(i))
                self.assertEqual(len(rows(self.path,'executions')),1);self.assertEqual(rows(self.path,'services')[0]['revision'],2)
                if i:
                    stored=rows(self.path,'executions')[0]['result_json'];self.admin(expected=2,now=1700);self.clock.now=0;self.execute()
                    self.assertEqual(rows(self.path,'executions')[0]['result_json'],stored);self.assertEqual(rows(self.path,'services')[0]['revision'],3)
                save(f'd10-{i}',{'barrier':point,'worker':worker.events,'held_sql':held,'reopened_sql':reopened,'final_sql':snapshot(self.path)})

import sqlite3
from approval_continuity_lab.processes import Worker
from tests.support.base import Case, asset, rows, snapshot, B
from tests.support.evidence import save


class ExecutionRace(Case):
    def test_both_orderings_and_same_id(self):
        for i,(a_role,b_role) in enumerate([('execute-a','execute-b'),('execute-b','execute-a'),('execute-same','execute-same')]):
            from approval_continuity_lab import Lab
            self.path=self.path.with_name(f'race{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            with Worker(self.path,a_role) as a, Worker(self.path,b_role) as b:
                a.reach('before_begin');b.reach('before_begin')
                a.release();a.reach('after_begin')
                b.release()
                # B has permission to attempt BEGIN while A holds the writer.
                self.assertNotIn('after_begin',b.events)
                ra=a.finish();rb=b.finish()
                self.code(ra);self.code(rb,'OK' if a_role==b_role else 'APPROVAL_CONSUMED')
                if a_role==b_role:self.assertTrue(rb['replayed'])
                state=snapshot(self.path)
                self.assertEqual(len(state['executions']),1);self.assertEqual(state['services'][0]['revision'],2)
                self.assertEqual(state['services'][0]['artifact_digest'],B)
                self.assertEqual(sum(x['to_status']=='consumed' for x in state['transitions']),1)
                save(f'd06-{i}',{'a':a.events,'b':b.events,'sql':state})

    def test_real_busy_then_explicit_retry(self):
        self.seed()
        with Worker(self.path,'execute-a') as a, Worker(self.path,'execute-b') as b:
            a.reach('before_begin');b.reach('before_begin')
            a.release()
            a.reach('after_begin')
            # Both real lock attempts share the hold, rather than spending two
            # sequential busy timeouts plus worker startup inside its 5s bound.
            b.release()
            c=sqlite3.connect(self.path,isolation_level=None,timeout=2)
            try:
                with self.assertRaises(sqlite3.OperationalError) as error:c.execute('BEGIN IMMEDIATE')
                self.assertEqual(error.exception.sqlite_errorcode,sqlite3.SQLITE_BUSY)
                busy_code=error.exception.sqlite_errorcode
            finally:c.close()
            rb=b.finish();self.code(rb,'STORAGE_BUSY');self.assertNotIn('after_begin',b.events)
            self.assertIsNone(a.process.poll())
            self.assertEqual(rows(self.path,'executions'),[])
            self.code(a.finish())
            with Worker(self.path,'execute-b') as retry:self.code(retry.finish(),'APPROVAL_CONSUMED')
            save('d06-busy',{'sqlite_errorcode':busy_code,'a':a.events,'b':b.events,'retry':retry.events,'sql':snapshot(self.path)})

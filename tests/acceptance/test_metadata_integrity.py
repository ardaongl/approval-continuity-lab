"""F1: validate already-loaded metadata, independently of SQL write checks."""
import hashlib
import sqlite3
import subprocess
import sys
from approval_continuity_lab import Lab
from approval_continuity_lab.models import EXITS, MAX_INT
from approval_continuity_lab.processes import Worker
from tests.support.base import Case, Clock, asset, snapshot, rows, AGENT, REVIEWER, OPERATOR, FIXTURES


def corrupt(path, field, value):
    # Test-only connection: permit invalid stored CHECK values, without
    # weakening the production schema or the application's next connection.
    with sqlite3.connect(path) as connection:
        connection.execute('PRAGMA ignore_check_constraints=ON')
        if field == 'missing':
            sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='meta_no_delete'").fetchone()[0]
            connection.execute('DROP TRIGGER meta_no_delete')
            connection.execute('DELETE FROM meta')
            connection.execute(sql)
        elif field == 'extra':
            connection.execute('INSERT INTO meta VALUES(2,1,1500)')
        else:
            assert field in ('singleton', 'schema_version', 'observed_time_floor_ms')
            connection.execute('UPDATE meta SET '+field+'=?', (value,))


class MetadataIntegrity(Case):
    def fresh(self, label, committed=False):
        self.path = self.path.with_name(label+'.sqlite')
        self.clock = Clock()
        self.lab = Lab.open(self.path, self.clock)
        self.seed()
        if committed:
            self.execute()

    def rejected_unchanged(self, operation=None):
        before = snapshot(self.path)
        file_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        calls = self.clock.calls
        r = (operation or (lambda: self.lab.execute(asset('execution-input.json'), AGENT)))()
        self.code(r, 'STATE_CORRUPT')
        self.assertEqual(EXITS[r['code']], 65)
        self.assertEqual(r['effect_status'], 'none')
        self.assertIsNone(r['data'])
        self.assertIsNone(r['observed_at_ms'])
        self.assertEqual(snapshot(self.path), before)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), file_hash)
        self.assertEqual(self.clock.calls, calls)
        from tests.support.evidence import save
        save('metadata/'+self.path.stem+'-'+str(len(self.observed)),
             dict(report=r, before=before, after=snapshot(self.path),
                  before_sha256=file_hash,
                  after_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()))
        return r

    def test_original_negative_floor_and_wrong_version(self):
        for i, (field, value) in enumerate((('observed_time_floor_ms', -1), ('schema_version', 2))):
            with self.subTest(field=field):
                self.fresh('original-'+str(i))
                corrupt(self.path, field, value)
                self.rejected_unchanged()
                self.assertEqual(rows(self.path, 'proposals')[0]['status'], 'approved')
                self.assertEqual(rows(self.path, 'services')[0]['revision'], 1)
                self.assertEqual(rows(self.path, 'executions'), [])

    def test_missing_wrong_and_extra_singleton(self):
        for field, value in (('missing', None), ('singleton', 2), ('extra', None)):
            with self.subTest(field=field):
                self.fresh(field)
                corrupt(self.path, field, value)
                self.rejected_unchanged()

    def test_stored_types_and_bounds(self):
        variants = [('observed_time_floor_ms', x) for x in (MAX_INT+1, 1.5, 'bad', b'1500')]
        variants += [('schema_version', x) for x in (0, -1, 1.5, 'bad', b'1')]
        for i, (field, value) in enumerate(variants):
            with self.subTest(field=field, value=value):
                self.fresh('type-bound-'+str(i))
                corrupt(self.path, field, value)
                self.rejected_unchanged()

    def test_valid_floor_boundaries(self):
        for floor in (0, 1, MAX_INT):
            with self.subTest(floor=floor):
                self.fresh('valid-'+str(floor))
                with sqlite3.connect(self.path) as c:
                    c.execute('UPDATE meta SET observed_time_floor_ms=?', (floor,))
                self.clock.now = max(floor, 1600)
                self.code(self.lab.inspect('proposal', 'p1', AGENT))
                self.assertEqual(rows(self.path, 'meta')[0]['observed_time_floor_ms'], self.clock.now)
                self.assertEqual(rows(self.path, 'services')[0]['revision'], 1)

    def test_corruption_precedes_historical_retry_and_caller(self):
        self.fresh('history', committed=True)
        corrupt(self.path, 'schema_version', 2)
        self.clock.now = 0
        self.rejected_unchanged()
        self.rejected_unchanged(lambda: self.lab.inspect('execution', 'x1', AGENT))
        self.rejected_unchanged(lambda: self.lab.execute(asset('execution-input.json'), {'actor_id':'req_b','context_id':'c2'}))
        self.assertEqual(len(rows(self.path, 'executions')), 1)
        self.assertEqual(rows(self.path, 'services')[0]['revision'], 2)

    def test_all_noninitializing_operations_validate_meta(self):
        self.seed()
        corrupt(self.path, 'schema_version', 2)
        update = dict(schema_version=1,kind='tool',id='deploy_artifact',expected_revision=1,changes={})
        operations = [lambda: self.lab.propose(asset('submission.json'),AGENT),
                      lambda: self.lab.decide(asset('decision-input.json'),REVIEWER),
                      lambda: self.lab.review('p1',AGENT),
                      lambda: self.lab.inspect('approval','a1',REVIEWER),
                      lambda: self.lab.revoke(dict(schema_version=1,proposal_id='p1'),REVIEWER),
                      lambda: self.lab.admin_update(update,OPERATOR)]
        for operation in operations:
            self.rejected_unchanged(operation)
        # Strict input validation still precedes storage integrity checks.
        before = snapshot(self.path)
        self.code(self.lab.execute({},AGENT),'INPUT_INVALID')
        self.assertEqual(snapshot(self.path),before)
        self.code(self.lab.initialize(asset('base-config.json'),OPERATOR),'STATE_EXISTS')
        self.assertEqual(snapshot(self.path),before)

    def test_corruption_after_connection_open_before_begin(self):
        self.seed()
        path = self.path
        class Observer:
            def reached(self, point):
                if point == 'before_begin':
                    corrupt(path, 'observed_time_floor_ms', -1)
        lab = Lab.open(path,self.clock,Observer())
        # Snapshot after injected corruption is the independent no-repair oracle.
        expected = snapshot(path)
        expected['meta'][0]['observed_time_floor_ms'] = -1
        self.code(lab.execute(asset('execution-input.json'),AGENT),'STATE_CORRUPT')
        self.assertEqual(snapshot(path), expected)

    def test_real_processes_cannot_bypass_corrupt_meta(self):
        self.seed()
        with Worker(self.path,'execute-a') as a, Worker(self.path,'execute-b') as b:
            a.reach('before_begin'); b.reach('before_begin')
            corrupt(self.path,'observed_time_floor_ms',-1)
            before = snapshot(self.path)
            self.code(a.finish(),'STATE_CORRUPT')
            self.code(b.finish(),'STATE_CORRUPT')
            self.assertEqual(a.process.returncode,65)
            self.assertEqual(b.process.returncode,65)
            self.assertEqual(snapshot(self.path),before)

    def test_cli_classification_and_no_writes(self):
        self.seed()
        corrupt(self.path,'schema_version',2)
        before = snapshot(self.path)
        p = subprocess.run([sys.executable,'-I','-B','-m','approval_continuity_lab','execute',
                            '--db',str(self.path),'--actor','req_a','--context','c1',
                            '--now-ms','1600','--input',str(FIXTURES/'execution-input.json')],capture_output=True,timeout=15)
        import json
        self.code(json.loads(p.stdout),'STATE_CORRUPT')
        self.assertEqual(p.returncode,65)
        self.assertEqual(p.stderr,b'acl: STATE_CORRUPT\n')
        self.assertEqual(snapshot(self.path),before)

    def test_normal_execution_and_historical_floor_semantics(self):
        self.seed()
        r = self.execute()
        self.assertEqual(rows(self.path,'meta')[0]['observed_time_floor_ms'],1600)
        before = snapshot(self.path)
        self.clock.now = 0
        retry = self.execute()
        self.assertTrue(retry['replayed'])
        self.assertEqual(retry['data']['result'],r['data']['result'])
        self.assertEqual(snapshot(self.path),before)

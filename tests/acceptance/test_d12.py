from pathlib import Path
import sqlite3
from unittest.mock import patch
from approval_continuity_lab import Lab
from approval_continuity_lab.store import Store
from tests.support.base import Case, asset, rows, snapshot, AGENT, OPERATOR, REVIEWER


class FailClosed(Case):
    def test_absent_existing_wrong_version_and_corrupt(self):
        self.execute(code='STORAGE_ERROR');self.assertFalse(self.path.exists())
        self.path.write_bytes(b'');self.code(self.lab.initialize(asset('base-config.json'),OPERATOR),'STATE_EXISTS');self.assertEqual(self.path.read_bytes(),b'')
        self.path.unlink();self.seed();before=snapshot(self.path)
        self.code(self.lab.initialize(asset('base-config.json'),OPERATOR),'STATE_EXISTS');self.assertEqual(snapshot(self.path),before)
        with sqlite3.connect(self.path) as c:c.execute('PRAGMA user_version=2')
        self.execute(code='DATABASE_VERSION')
        self.path=self.path.with_name('bad.sqlite');self.path.write_bytes(b'not sqlite');self.lab=Lab.open(self.path,self.clock)
        self.execute(code='STATE_CORRUPT')

    def test_loaded_canonical_corruption_fails_closed(self):
        self.seed()
        with sqlite3.connect(self.path) as c:
            sql=c.execute("SELECT sql FROM sqlite_master WHERE name='decisions_immutable'").fetchone()[0]
            c.execute('DROP TRIGGER decisions_immutable')
            c.execute("UPDATE decisions SET decision_digest=?",('0'*64,))
            c.execute(sql)
        self.execute(code='STATE_CORRUPT');self.unchanged_effect()

    def test_real_sqlite_authorizer_write_failure_rolls_back(self):
        self.seed();before=snapshot(self.path);connect=Store.connect;denied=[]
        def fault(s,*args,**kwargs):
            connect(s,*args,**kwargs)
            def authorize(action,arg1,arg2,db,trigger):
                if action==sqlite3.SQLITE_INSERT and arg1=='executions':
                    denied.append((action,arg1));return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            s.connection.set_authorizer(authorize)
        with patch.object(Store,'connect',fault):self.execute(code='STORAGE_ERROR')
        self.assertTrue(denied);self.assertEqual(snapshot(self.path),before)

    def test_commit_busy_is_known_rollback(self):
        self.seed();before=snapshot(self.path)
        reader=sqlite3.connect(self.path,isolation_level=None)
        try:
            reader.execute('BEGIN');reader.execute('SELECT * FROM services').fetchall()
            r=self.execute(code='STORAGE_BUSY');self.assertEqual(r['effect_status'],'none')
        finally:reader.close()
        self.assertEqual(snapshot(self.path),before)

    def test_uncertain_commit_preserves_durable_result_and_identity_reconciliation(self):
        self.seed();commit=Store.commit
        def ambiguous(s):
            commit(s)
            error=sqlite3.OperationalError('injected delivery ambiguity after actual commit')
            error.sqlite_errorcode=sqlite3.SQLITE_IOERR
            raise error
        with patch.object(Store,'commit',ambiguous):
            r=self.execute(code='STORAGE_ERROR');self.assertEqual(r['effect_status'],'unknown');self.assertIsNone(r['data'])
        self.assertEqual(rows(self.path,'services')[0]['revision'],2)
        self.assertEqual(len(rows(self.path,'executions')),1)
        self.assertTrue(self.execute()['replayed']);self.assertEqual(rows(self.path,'services')[0]['revision'],2)

    def test_observer_failures_before_and_after_commit(self):
        self.seed();before=snapshot(self.path)
        class Observer:
            def __init__(self,where):self.where=where
            def reached(self,point):
                if point==self.where:raise RuntimeError('synthetic observer failure')
        r=Lab.open(self.path,self.clock,Observer('before_commit')).execute(asset('execution-input.json'),AGENT)
        self.code(r,'INTERNAL_ERROR');self.assertEqual(snapshot(self.path),before)
        r=Lab.open(self.path,self.clock,Observer('after_commit_before_response')).execute(asset('execution-input.json'),AGENT)
        self.code(r,'INTERNAL_ERROR');self.assertEqual(r['effect_status'],'committed');self.assertIsNotNone(r['data']['result'])
        self.assertEqual(len(rows(self.path,'executions')),1)

    def test_sql_constraints_and_immutable_history(self):
        self.seed();before=snapshot(self.path)
        failures=[("UPDATE decisions SET decided_at_ms=-1",()),("UPDATE decisions SET canonical_decision='{}'",()),("UPDATE proposals SET canonical_proposal='{}'",()),("UPDATE services SET revision=0",()),("UPDATE actors SET role='admin'",()),("DELETE FROM decisions",()),("UPDATE proposals SET reviewer_id='missing'",()),("INSERT INTO executions SELECT * FROM executions",())]
        for sql,args in failures[:-1]:
            with sqlite3.connect(self.path) as c:
                c.execute('PRAGMA foreign_keys=ON')
                with self.assertRaises(sqlite3.IntegrityError):c.execute(sql,args)
            self.assertEqual(snapshot(self.path),before)
        self.execute()
        with sqlite3.connect(self.path) as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute('INSERT INTO executions SELECT * FROM executions')
            with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE proposals SET status='approved'")

    def test_invalid_facade_construction_is_no_io(self):
        for path,clock in [(None,self.clock),('',self.clock),(self.path,None)]:
            with self.assertRaises(ValueError):Lab.open(path,clock)
        self.assertFalse(self.path.exists())
        # The independent oracle must never create the absent state it is
        # supposed to observe, including when collecting failure evidence.
        with self.assertRaises(sqlite3.OperationalError):snapshot(self.path)
        self.assertFalse(self.path.exists())

    def test_init_symlinks_and_missing_parent(self):
        self.path.symlink_to(self.path.with_name('other.sqlite'))
        self.code(self.lab.initialize(asset('base-config.json'),OPERATOR),'STORAGE_ERROR')
        self.assertFalse(self.path.with_name('other.sqlite').exists())
        lab=Lab.open(self.path.parent/'missing'/'db',self.clock)
        self.code(lab.initialize(asset('base-config.json'),OPERATOR),'STORAGE_ERROR')

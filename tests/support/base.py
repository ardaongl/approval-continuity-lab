"""Test-owned input assets and independent raw SQL observations."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from approval_continuity_lab import Lab

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/fixtures"
AGENT = {"actor_id": "req_a", "context_id": "c1"}
REVIEWER = {"actor_id": "rev_a", "context_id": None}
OPERATOR = {"actor_id": "op", "context_id": None}
A, B, C = ("sha256:" + c * 64 for c in "abc")


def asset(name):
    return json.loads((FIXTURES / name).read_bytes())


class Clock:
    def __init__(self, now=1000):
        self.now = now
        self.calls = 0

    def now_ms(self):
        self.calls += 1
        return self.now


def rows(path, table):
    assert table in ("meta", "actors", "contexts", "tools", "policies", "eligibility", "services", "proposals", "decisions", "executions", "transitions")
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=rw', uri=True)) as c:
        c.row_factory = sqlite3.Row
        return [dict(x) for x in c.execute("SELECT * FROM " + table + " ORDER BY 1")]


def snapshot(path):
    return {table: rows(path, table) for table in ("meta", "actors", "contexts", "tools", "policies", "eligibility", "services", "proposals", "decisions", "executions", "transitions")}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "lab.sqlite"
        self.clock = Clock()
        self.lab = Lab.open(self.path, self.clock)
        self.observed = []

    def tearDown(self):
        from tests.support.evidence import save
        databases = {}
        for path in Path(self.tmp.name).rglob('*.sqlite'):
            try:
                databases[str(path.relative_to(self.tmp.name))] = snapshot(path)
            except sqlite3.Error as error:
                databases[str(path.relative_to(self.tmp.name))] = {'sqlite_error':type(error).__name__}
        save('cases/'+self.id(), {'reports_and_expected_codes':self.observed,'raw_sql':databases})

    def code(self, r, expected="OK"):
        self.observed.append({'expected_code':expected,'observed_report':json.loads(json.dumps(r,ensure_ascii=True))})
        self.assertEqual(r["code"], expected, r)
        return r

    def seed(self, approved=True, config=None, submission=None):
        self.clock.now = 1000
        self.code(self.lab.initialize(config or asset("base-config.json"), OPERATOR))
        self.code(self.lab.propose(submission or asset("submission.json"), AGENT))
        if approved:
            self.clock.now = 1500
            self.code(self.lab.decide(asset("decision-input.json"), REVIEWER))
        self.clock.now = 1600

    def execute(self, body=None, caller=None, code="OK"):
        return self.code(self.lab.execute(body or asset("execution-input.json"), caller or AGENT), code)

    def admin(self, kind="service", id="svc1", changes=None, expected=1, now=1550):
        self.clock.now = now
        defaults = {"service": {"artifact_digest": C}, "context": {"executor_id": "ex3"}, "tool": {}, "policy": {"enabled": False}, "eligibility": {"allowed": False}}
        body = dict(schema_version=1, kind=kind, id=id, expected_revision=expected, changes=defaults[kind] if changes is None else changes)
        if kind == "eligibility":
            body["reviewer_id"] = "rev_a"
        return self.code(self.lab.admin_update(body, OPERATOR))

    def unchanged_effect(self, status="approved", artifact=A, revision=1):
        self.assertEqual(rows(self.path, "services")[0]["artifact_digest"], artifact)
        self.assertEqual(rows(self.path, "services")[0]["revision"], revision)
        self.assertEqual(rows(self.path, "proposals")[0]["status"], status)
        self.assertEqual(rows(self.path, "executions"), [])

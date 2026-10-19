"""Sole SQL issuer. Every command uses one explicit writer transaction."""
import json
import os
from pathlib import Path
import sqlite3
from .canonical import canonical, digest
from .models import Failure, MAX_INT, STATES, add, require
from . import validation as v


TABLES = {
    "meta": "singleton schema_version observed_time_floor_ms",
    "actors": "actor_id role",
    "contexts": "context_id requester_id agent_id run_id tenant environment executor_id revision",
    "tools": "tool_id revision",
    "policies": "tenant revision enabled",
    "eligibility": "tenant reviewer_id revision allowed",
    "services": "service_id tenant environment display_name artifact_digest revision",
    "proposals": "proposal_id request_id context_id reviewer_id target_service_id canonical_proposal proposal_digest canonical_review review_digest submission_json description status status_reason replacement_id status_at_ms",
    "decisions": "approval_id proposal_id canonical_decision decision_digest submission_json reviewer_id decided_at_ms expires_at_ms",
    "executions": "execution_id approval_id proposal_id requester_id context_id request_json request_digest result_json authorized_at_ms before_revision after_revision",
    "transitions": "proposal_id sequence from_status to_status reason at_ms",
}
KEYS = {t: s.split()[0] for t, s in TABLES.items()}
REASONS = ("REVIEW_REJECTED", "PENDING_EXPIRED", "GRANT_EXPIRED", "CONTEXT_CHANGED", "TOOL_CHANGED", "POLICY_CHANGED", "REVIEWER_CHANGED", "TARGET_REVISION_CHANGED", "REPLACED")
NULLABLE = {"status_reason", "replacement_id", "expires_at_ms", "from_status", "reason"}
INTS = {"singleton", "schema_version", "observed_time_floor_ms", "revision", "status_at_ms", "decided_at_ms", "expires_at_ms", "authorized_at_ms", "before_revision", "after_revision", "sequence", "at_ms"}
BOOLS = {"enabled", "allowed"}
FK = {
    ("contexts", "requester_id"): ("actors", "actor_id"),
    ("eligibility", "tenant"): ("policies", "tenant"),
    ("eligibility", "reviewer_id"): ("actors", "actor_id"),
    ("proposals", "context_id"): ("contexts", "context_id"),
    ("proposals", "reviewer_id"): ("actors", "actor_id"),
    ("proposals", "target_service_id"): ("services", "service_id"),
    ("proposals", "replacement_id"): ("proposals", "proposal_id"),
    ("decisions", "proposal_id"): ("proposals", "proposal_id"),
    ("decisions", "reviewer_id"): ("actors", "actor_id"),
    ("executions", "approval_id"): ("decisions", "approval_id"),
    ("executions", "proposal_id"): ("proposals", "proposal_id"),
    ("executions", "requester_id"): ("actors", "actor_id"),
    ("executions", "context_id"): ("contexts", "context_id"),
    ("transitions", "proposal_id"): ("proposals", "proposal_id"),
}


def enum(column, values):
    return column + " IN (" + ",".join("'" + x + "'" for x in values) + ")"


def schema():
    statements = []
    for table, cols in TABLES.items():
        definitions = []
        for col in cols.split():
            nullable = col in NULLABLE
            if col in INTS | BOOLS:
                low = 1 if col in {"revision", "before_revision", "after_revision", "sequence"} else 0
                condition = f"typeof({col})='integer' AND {col} BETWEEN {low} AND {MAX_INT}"
                if col in BOOLS:
                    condition = f"typeof({col})='integer' AND {col} IN (0,1)"
                if col in {"singleton", "schema_version"}:
                    condition += f" AND {col}=1"
                sqltype = "INTEGER"
            else:
                condition = f"typeof({col})='text'"
                sqltype = "TEXT"
                if col in {"status", "from_status", "to_status"}:
                    condition += " AND " + enum(col, STATES)
                if col in {"reason", "status_reason"}:
                    condition += " AND " + enum(col, REASONS)
                if col == "role":
                    condition += " AND " + enum(col, ("operator", "agent", "reviewer"))
                if col == "tool_id":
                    condition += f" AND {col}='deploy_artifact'"
                if col.endswith("_digest") and col != "artifact_digest":
                    condition += f" AND length({col})=64 AND {col} NOT GLOB '*[^0-9a-f]*'"
                elif col == "artifact_digest":
                    condition += f" AND length({col})=71 AND substr({col},1,7)='sha256:' AND substr({col},8) NOT GLOB '*[^0-9a-f]*'"
                elif (col.endswith("_id") or col in {"tenant", "environment"}) and col != "tool_id":
                    condition += f" AND length({col}) BETWEEN 1 AND 64 AND substr({col},1,1) GLOB '[a-z]' AND {col} NOT GLOB '*[^a-z0-9_-]*'"
            if nullable:
                condition = f"{col} IS NULL OR ({condition})"
            part = f"{col} {sqltype}" + ("" if nullable else " NOT NULL") + f" CHECK({condition})"
            if (table, col) in FK:
                target, key = FK[table, col]
                part += f" REFERENCES {target}({key}) ON DELETE RESTRICT"
            definitions.append(part)
        primary = "tenant,reviewer_id" if table == "eligibility" else "proposal_id,sequence" if table == "transitions" else KEYS[table]
        definitions.append("PRIMARY KEY(" + primary + ")")
        if table in {"decisions", "executions"}:
            definitions.append("UNIQUE(proposal_id)")
        if table == "executions":
            definitions.extend(["UNIQUE(approval_id)", "CHECK(after_revision=before_revision+1)"])
        if table == "proposals":
            definitions.append("UNIQUE(request_id)")
        statements.append("CREATE TABLE " + table + "(" + ",".join(definitions) + ")")
        statements.append(f"CREATE TRIGGER {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT,'immutable history'); END")
        immutable = cols.split() if table in {"actors", "decisions", "executions", "transitions"} else []
        if table == "proposals":
            immutable = [x for x in cols.split() if x not in {"status", "status_reason", "status_at_ms", "replacement_id"}]
        if table == "contexts":
            immutable = [x for x in cols.split() if x not in {"executor_id", "revision"}]
        if table == "services":
            immutable = [x for x in cols.split() if x not in {"artifact_digest", "revision"}]
        if immutable:
            condition = " OR ".join(f"NEW.{x} IS NOT OLD.{x}" for x in immutable)
            statements.append(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE ON {table} WHEN {condition} BEGIN SELECT RAISE(ABORT,'immutable content'); END")
    statements.append("CREATE TRIGGER proposal_terminal BEFORE UPDATE OF status ON proposals WHEN NEW.status!=OLD.status AND NOT ((OLD.status='pending' AND NEW.status IN ('approved','rejected','expired','superseded')) OR (OLD.status='approved' AND NEW.status IN ('consumed','revoked','expired','superseded'))) BEGIN SELECT RAISE(ABORT,'terminal status'); END")
    statements.append("CREATE TRIGGER replacement_once BEFORE UPDATE OF replacement_id ON proposals WHEN OLD.replacement_id IS NOT NULL AND NEW.replacement_id IS NOT OLD.replacement_id BEGIN SELECT RAISE(ABORT,'immutable replacement'); END")
    return statements


def storage_code(exc):
    code = getattr(exc, "sqlite_errorcode", 0) & 255
    if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
        return "STORAGE_BUSY"
    if code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_CONSTRAINT):
        return "STATE_CORRUPT"
    return "STORAGE_ERROR"


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.connection = None
        self.created = False

    def connect(self, create=False):
        require(not self.path.is_symlink(), "STORAGE_ERROR")
        self.path = self.path.resolve()
        if create:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                self.created = True
            except FileExistsError:
                raise Failure("STATE_EXISTS")
        self.connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=2)
        self.connection.row_factory = sqlite3.Row
        # Do not convert an unrelated existing WAL database before schema checks.
        if not create:
            require(self.connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete", "STATE_CORRUPT")
        for statement in (("PRAGMA journal_mode=DELETE",) if create else ()) + ("PRAGMA synchronous=FULL", "PRAGMA foreign_keys=ON", "PRAGMA busy_timeout=2000", "PRAGMA cache_spill=OFF"):
            self.connection.execute(statement)

    def begin(self):
        self.connection.execute("BEGIN IMMEDIATE")

    def initialize(self, config, now):
        for statement in schema():
            self.connection.execute(statement)
        self.connection.execute("PRAGMA application_id=0x41434C31")
        self.connection.execute("PRAGMA user_version=1")
        self.insert("meta", dict(singleton=1, schema_version=1, observed_time_floor_ms=now))
        for name in v.CONFIG_ROWS:
            for item in config[name]:
                self.insert(name, {k: int(val) if type(val) is bool else val for k, val in item.items()})

    def check_schema(self):
        require(self.connection.execute("PRAGMA application_id").fetchone()[0] == 0x41434C31 and self.connection.execute("PRAGMA user_version").fetchone()[0] == 1, "DATABASE_VERSION")
        names = {r[0] for r in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require(names == set(TABLES), "DATABASE_VERSION")
        for table, cols in TABLES.items():
            require([r[1] for r in self.connection.execute(f"PRAGMA table_info({table})")] == cols.split(), "DATABASE_VERSION")
        triggers = {r[0] for r in self.connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        expected = {s.split()[2] for s in schema() if s.startswith("CREATE TRIGGER")}
        require(expected <= triggers, "DATABASE_VERSION")
        # SQL constraints protect writes, not already-corrupt loaded state.
        # Validate inside BEGIN IMMEDIATE, before caller/history/time checks.
        metadata = self.all("meta")
        require(len(metadata) == 1, "STATE_CORRUPT")
        meta = metadata[0]
        require(type(meta["singleton"]) is int and meta["singleton"] == 1
                and type(meta["schema_version"]) is int and meta["schema_version"] == 1
                and type(meta["observed_time_floor_ms"]) is int
                and 0 <= meta["observed_time_floor_ms"] <= MAX_INT,
                "STATE_CORRUPT")

    def one(self, table, **where):
        rows = self.all(table, **where)
        return rows[0] if rows else None

    def all(self, table, **where):
        assert table in TABLES and set(where) <= set(TABLES[table].split())
        condition = " AND ".join(k + "=?" for k in where) or "1"
        return [dict(r) for r in self.connection.execute("SELECT * FROM " + table + " WHERE " + condition, tuple(where.values()))]

    def insert(self, table, row):
        assert table in TABLES and set(row) == set(TABLES[table].split())
        self.connection.execute("INSERT INTO " + table + "(" + ",".join(row) + ") VALUES(" + ",".join("?" for _ in row) + ")", tuple(row.values()))

    def update(self, table, changes, **where):
        assert table in TABLES and set(changes) | set(where) <= set(TABLES[table].split()) and where
        sql = "UPDATE " + table + " SET " + ",".join(k + "=?" for k in changes) + " WHERE " + " AND ".join(k + "=?" for k in where)
        return self.connection.execute(sql, (*changes.values(), *where.values())).rowcount

    def count(self, table, **where):
        return len(self.all(table, **where))

    def room(self, table, **where):
        require(self.count(table, **where) < (8 if table == "transitions" else 1000), "LIMIT_EXCEEDED")

    def transition(self, row, to, reason, now):
        self.room("transitions", proposal_id=row["proposal_id"])
        self.insert("transitions", dict(proposal_id=row["proposal_id"], sequence=self.count("transitions", proposal_id=row["proposal_id"]) + 1, from_status=row.get("status"), to_status=to, reason=reason, at_ms=now))
        self.update("proposals", dict(status=to, status_reason=reason, status_at_ms=now), proposal_id=row["proposal_id"])
        row.update(status=to, status_reason=reason, status_at_ms=now)

    def canonical_record(self, row, column, domain=None, hash_column=None):
        try:
            value = v.decode(row[column].encode("utf-8"))
            require(canonical(value) == row[column], "STATE_CORRUPT")
            if domain:
                require(digest(domain, value) == row[hash_column], "STATE_CORRUPT")
            return value
        except (Failure, KeyError, TypeError, AttributeError):
            raise Failure("STATE_CORRUPT")

    def proposal(self, row):
        p = self.canonical_record(row, "canonical_proposal", "proposal", "proposal_digest")
        try:
            v.obj(p, v.PROPOSAL)
            r = self.canonical_record(row, "canonical_review", "review", "review_digest")
            sub = self.canonical_record(row, "submission_json")
            v.validate("propose", sub)
            require(r == dict(kind="approval-review-v1", proposal=p), "STATE_CORRUPT")
            for name in ("proposal_id", "request_id", "context_id", "reviewer_id", "target_service_id"):
                require(row[name] == p[name], "STATE_CORRUPT")
            require(row["description"] == sub["description"], "STATE_CORRUPT")
            for name in sub.keys() - {"description"}:
                require(p[name] == sub[name], "STATE_CORRUPT")
            step = p["plan"]["steps"][0]
            require(p["plan_digest"] == digest("plan", p["plan"]) and p["selected_step_id"] == step["step_id"] and p["tool_id"] == step["tool_id"] and p["target_service_id"] == step["arguments"]["service_id"], "STATE_CORRUPT")
            history = self.all("transitions", proposal_id=p["proposal_id"])
            history.sort(key=lambda r: r["sequence"])
            require(bool(history) and history[-1]["to_status"] == row["status"] and history[-1]["reason"] == row["status_reason"] and history[-1]["at_ms"] == row["status_at_ms"], "STATE_CORRUPT")
            previous = None
            for i, h in enumerate(history, 1):
                require(h["sequence"] == i and h["from_status"] == previous and h["to_status"] in STATES, "STATE_CORRUPT")
                allowed = {None: ("pending",), "pending": ("approved", "rejected", "expired", "superseded"), "approved": ("consumed", "revoked", "expired", "superseded")}.get(previous, ())
                require(h["to_status"] in allowed, "STATE_CORRUPT")
                previous = h["to_status"]
            d = self.one("decisions", proposal_id=p["proposal_id"])
            if row["status"] in ("approved", "rejected", "consumed", "revoked"):
                require(d is not None, "STATE_CORRUPT")
            if d:
                decision = self.decision(d, p, row)
                require((decision["decision"] == "reject") == (row["status"] == "rejected"), "STATE_CORRUPT")
            executions = self.all("executions", proposal_id=p["proposal_id"])
            require((len(executions) == 1) == (row["status"] == "consumed"), "STATE_CORRUPT")
            for e in executions:
                self.execution(e, p, d)
            return p
        except (Failure, KeyError, TypeError, ValueError):
            raise Failure("STATE_CORRUPT")

    def decision(self, row, p, proposal_row):
        d = self.canonical_record(row, "canonical_decision", "decision", "decision_digest")
        sub = self.canonical_record(row, "submission_json")
        try:
            v.validate("decide", sub)
            expected = dict(sub, proposal_digest=proposal_row["proposal_digest"], reviewer_id=p["reviewer_id"], decided_at_ms=row["decided_at_ms"], expires_at_ms=row["expires_at_ms"])
            require(d == expected and d["proposal_id"] == p["proposal_id"] and d["approval_id"] == row["approval_id"] and row["reviewer_id"] == p["reviewer_id"] and d["review_digest"] == proposal_row["review_digest"], "STATE_CORRUPT")
            expiry = add(d["decided_at_ms"], p["grant_ttl_ms"]) if d["decision"] == "approve" else None
            require(d["expires_at_ms"] == expiry, "STATE_CORRUPT")
            return d
        except (Failure, KeyError, TypeError):
            raise Failure("STATE_CORRUPT")

    def execution(self, row, p, decision):
        request = self.canonical_record(row, "request_json", "execution", "request_digest")
        result = self.canonical_record(row, "result_json")
        try:
            body = {k: val for k, val in request.items() if k not in ("actor_id", "context_id")}
            v.validate("execute", body)
            require(request["actor_id"] == row["requester_id"] == p["requester_id"] and request["context_id"] == row["context_id"] == p["context_id"], "STATE_CORRUPT")
            require(request["execution_id"] == row["execution_id"] and request["approval_id"] == row["approval_id"] == decision["approval_id"] and request["intent"]["binding"] == p, "STATE_CORRUPT")
            require(request["intent"]["proposal_id"] == p["proposal_id"] and request["intent"]["proposal_digest"] == digest("proposal", p) and request["intent"]["review_digest"] == digest("review", {"kind": "approval-review-v1", "proposal": p}), "STATE_CORRUPT")
            expected = dict(approval_id=row["approval_id"], execution_id=row["execution_id"], proposal_id=p["proposal_id"], service_id=p["target_service_id"], tenant=p["tenant"], environment=p["environment"], artifact_digest=p["plan"]["steps"][0]["arguments"]["artifact_digest"], before_revision=p["expected_target_revision"], after_revision=add(p["expected_target_revision"], 1), authorized_at_ms=row["authorized_at_ms"])
            require(result == expected and row["before_revision"] == expected["before_revision"] and row["after_revision"] == expected["after_revision"], "STATE_CORRUPT")
            return result
        except (Failure, KeyError, TypeError):
            raise Failure("STATE_CORRUPT")

    def commit(self):
        self.connection.execute("COMMIT")

    def rollback(self):
        if self.connection and self.connection.in_transaction:
            self.connection.rollback()

    def close(self):
        if self.connection:
            self.connection.close()

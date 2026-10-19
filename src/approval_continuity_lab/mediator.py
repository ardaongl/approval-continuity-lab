"""Approval state machine. Authorization and reference effects share one lock."""
import os
import sqlite3
from pathlib import Path
from .canonical import canonical, digest
from .models import Failure, MAX_INT, DAY, add, require
from .report import report, set_error, serialize
from .store import Store, storage_code
from . import validation as v


class Lab:
    @classmethod
    def open(cls, path, clock, observer=None, cancellation=None):
        return cls(path, clock, observer, cancellation)

    def __init__(self, path, clock, observer=None, cancellation=None):
        if not isinstance(path, (str, os.PathLike)) or not str(path) or "\0" in str(path):
            raise ValueError("Invalid database path")
        if not callable(getattr(clock, "now_ms", None)):
            raise ValueError("Clock.now_ms is required")
        if observer is not None and not callable(getattr(observer, "reached", None)):
            raise ValueError("Observer.reached is required")
        if cancellation is not None and not callable(getattr(cancellation, "is_cancelled", None)):
            raise ValueError("Cancellation.is_cancelled is required")
        self.path, self.clock, self.observer, self.cancellation = path, clock, observer, cancellation

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def _point(self, name):
        if self.observer:
            self.observer.reached(name)

    def _cancelled(self):
        return self.cancellation is not None and self.cancellation.is_cancelled()

    def initialize(self, config, caller):
        return self._command("init", config, caller)

    def propose(self, command, caller):
        return self._command("propose", command, caller)

    def decide(self, command, caller):
        return self._command("decide", command, caller)

    def execute(self, command, caller):
        return self._command("execute", command, caller)

    def revoke(self, command, caller):
        return self._command("revoke", command, caller)

    def review(self, proposal_id, caller):
        return self._command("review", {"proposal_id": proposal_id}, caller)

    def inspect(self, kind, id, caller):
        return self._command("inspect", {"kind": kind, "id": id}, caller)

    def admin_update(self, command, caller):
        return self._command("admin-update", command, caller)

    def _command(self, name, body, caller):
        r = report(name)
        s, sampled, committed, commit_started, original_status = Store(self.path), False, False, False, None
        try:
            v.validate(name, body)
            v.generic(caller)
            v.obj(caller, {"actor_id": "id", "context_id": "id?"})
            require(not self._cancelled(), "INTERRUPTED")
            s.connect(create=name == "init")
            self._point("before_begin")
            require(not self._cancelled(), "INTERRUPTED")
            s.begin()
            self._point("after_begin")
            if name == "init":
                actors = {x["actor_id"]: x["role"] for x in body["actors"]}
                require(actors.get(caller["actor_id"]) == "operator", "ROLE_FORBIDDEN")
                require(caller["context_id"] is None, "CALLER_MISMATCH")
                now = self._time()
                s.initialize(body, now)
                sampled = True
                r.update(observed_at_ms=now, data={"schema_version": 1})
            else:
                s.check_schema()
                actor, context = self._caller(s, caller, name)
                row, p, d, e, old = self._lookup(s, name, body, caller, actor, context)
                if row:
                    original_status = row["status"]
                    r.update(proposal_id=row["proposal_id"], status=row["status"])
                    if d:
                        r["approval_id"] = d["approval_id"]
                    if name == "execute":
                        r["execution_id"] = body["execution_id"]
                    elif e:
                        r["execution_id"] = e["execution_id"]
                historical = self._retry(s, name, body, caller, r, row, p, d, e, old)
                if not historical:
                    now = self._time()
                    meta = s.one("meta", singleton=1)
                    require(now >= meta["observed_time_floor_ms"], "CLOCK_REGRESSION")
                    s.update("meta", {"observed_time_floor_ms": now}, singleton=1)
                    r["observed_at_ms"] = now
                    sampled = True
                    if row:
                        self._reconcile(s, row, p, d, now, r)
                    try:
                        if name == "propose":
                            self._propose(s, body, caller, context, old, now, r)
                        elif name == "decide":
                            self._decide(s, body, caller, row, p, now, r)
                        elif name in ("review", "inspect"):
                            self._read(s, name, body, row, p, d, e, r)
                        elif name == "execute":
                            self._execute(s, body, caller, row, p, d, now, r)
                        elif name == "revoke":
                            self._revoke(s, row, now, r)
                        elif name == "admin-update":
                            self._admin(s, body, r)
                    except Failure as exc:
                        # Domain/input arithmetic denial may persist the valid
                        # time observation and required lazy reconciliation.
                        if exc.code in ("STATE_CORRUPT", "STORAGE_ERROR", "INTERNAL_ERROR"):
                            raise
                        set_error(r, exc.code, exc.details)
                else:
                    sampled = False
            if not (name == "execute" and r["code"] == "OK" and not r["replayed"]):
                self._point("after_checks")
            # Both possible formats must fit before COMMIT.
            serialize(r, "json")
            serialize(r, "text")
            self._point("before_commit")
            require(not self._cancelled(), "INTERRUPTED")
            commit_started = True
            s.commit()
            committed = True
            self._point("after_commit_before_response")
            if self._cancelled():
                r.update(code="INTERRUPTED", outcome="interrupted")
            return r
        except Failure as exc:
            if committed:
                r.update(code=exc.code, outcome="interrupted" if exc.code == "INTERRUPTED" else "error")
                return r
            s.rollback()
            set_error(r, exc.code, exc.details)
        except sqlite3.Error as exc:
            code = storage_code(exc)
            uncertain = commit_started and not committed and not (code == "STORAGE_BUSY" and s.connection.in_transaction)
            s.rollback()
            set_error(r, "INTERRUPTED" if self._cancelled() else code)
            if uncertain:
                r["effect_status"] = "unknown"
        except OSError:
            s.rollback()
            set_error(r, "STORAGE_ERROR")
        except Exception:
            if committed:
                r.update(code="INTERNAL_ERROR", outcome="error")
                return r
            s.rollback()
            set_error(r, "INTERNAL_ERROR")
        finally:
            s.close()
            if s.created and not committed and not (commit_started and r["effect_status"] == "unknown"):
                # Only the exclusively created, proven noncommitted init file.
                try:
                    s.path.unlink()
                except FileNotFoundError:
                    pass
        r["observed_at_ms"] = None
        if r["effect_status"] != "unknown":
            r["effect_status"] = "none"
        r["authorized_at_ms"] = None
        r["status"] = original_status
        return r

    def _time(self):
        now = self.clock.now_ms()
        require(type(now) is int and 0 <= now <= MAX_INT, "INPUT_INVALID")
        return now

    def _caller(self, s, caller, name):
        actor = s.one("actors", actor_id=caller["actor_id"])
        require(actor is not None, "ROLE_FORBIDDEN")
        role = actor["role"]
        require(role in ("operator", "reviewer", "agent"), "STATE_CORRUPT")
        allowed = {"propose": ("agent",), "execute": ("agent",), "decide": ("reviewer",), "revoke": ("reviewer", "operator"), "admin-update": ("operator",)}.get(name, ("agent", "reviewer", "operator"))
        require(role in allowed, "ROLE_FORBIDDEN")
        context = None
        if role == "agent":
            require(caller["context_id"] is not None, "CALLER_MISMATCH")
            context = s.one("contexts", context_id=caller["context_id"])
            require(context is not None and context["requester_id"] == caller["actor_id"], "CALLER_MISMATCH")
            self._validate_row("contexts", context)
        else:
            require(caller["context_id"] is None, "CALLER_MISMATCH")
        return actor, context

    def _validate_row(self, table, row):
        require(row is not None, "STATE_CORRUPT")
        x = dict(row)
        for name in ("enabled", "allowed"):
            if name in x:
                require(type(x[name]) is int and x[name] in (0, 1), "STATE_CORRUPT")
                x[name] = bool(x[name])
        try:
            v.generic(x)
            v.obj(x, v.CONFIG_ROWS[table])
        except Failure:
            raise Failure("STATE_CORRUPT")
        return row

    def _lookup(self, s, name, body, caller, actor, context):
        row = p = d = e = old = None
        if name == "propose":
            require(body["context_id"] == caller["context_id"], "CALLER_MISMATCH")
            require(s.one("services", service_id=body["plan"]["steps"][0]["arguments"]["service_id"]) is not None, "NOT_FOUND")
            if body["replaces_proposal_id"] is not None:
                old = s.one("proposals", proposal_id=body["replaces_proposal_id"])
                require(old is not None, "NOT_FOUND")
                previous = s.proposal(old)
                require(previous["context_id"] == caller["context_id"] and previous["requester_id"] == caller["actor_id"], "CALLER_MISMATCH")
        elif name in ("execute", "decide", "review", "revoke", "inspect"):
            if name == "execute":
                d = s.one("decisions", approval_id=body["approval_id"])
                require(d is not None, "NOT_FOUND")
                row = s.one("proposals", proposal_id=d["proposal_id"])
            elif name == "inspect" and body["kind"] == "approval":
                d = s.one("decisions", approval_id=body["id"])
                require(d is not None, "NOT_FOUND")
                row = s.one("proposals", proposal_id=d["proposal_id"])
            elif name == "inspect" and body["kind"] == "execution":
                e = s.one("executions", execution_id=body["id"])
                require(e is not None, "NOT_FOUND")
                row = s.one("proposals", proposal_id=e["proposal_id"])
            else:
                row = s.one("proposals", proposal_id=body["id"] if name == "inspect" else body["proposal_id"])
            require(row is not None, "NOT_FOUND")
            p = s.proposal(row)
            if actor["role"] == "agent":
                require(p["requester_id"] == caller["actor_id"] and p["context_id"] == caller["context_id"], "CALLER_MISMATCH")
            elif actor["role"] == "reviewer":
                require(p["reviewer_id"] == caller["actor_id"], "CALLER_MISMATCH")
            if d is None:
                d = s.one("decisions", proposal_id=row["proposal_id"])
        elif name == "admin-update":
            table, key = {"service": ("services", "service_id"), "context": ("contexts", "context_id"), "tool": ("tools", "tool_id"), "policy": ("policies", "tenant"), "eligibility": ("eligibility", "tenant")}[body["kind"]]
            where = {key: body["id"]}
            if body["kind"] == "eligibility":
                where["reviewer_id"] = body["reviewer_id"]
            require(s.one(table, **where) is not None, "NOT_FOUND")
        return row, p, d, e, old

    def _retry(self, s, name, body, caller, r, row, p, d, e, old):
        if name == "propose":
            a = s.one("proposals", proposal_id=body["proposal_id"])
            b = s.one("proposals", request_id=body["request_id"])
            if a or b:
                require(a is not None and b is not None and a["proposal_id"] == b["proposal_id"], "IDEMPOTENCY_CONFLICT")
                p0 = s.proposal(a)
                require(p0["context_id"] == caller["context_id"] and p0["requester_id"] == caller["actor_id"] and a["submission_json"] == canonical(body), "IDEMPOTENCY_CONFLICT")
                r.update(proposal_id=p0["proposal_id"], replayed=True, status=None, data=self._proposal_data(a, p0))
                return True
        elif name == "decide":
            existing = s.one("decisions", approval_id=body["approval_id"])
            if existing:
                require(existing["submission_json"] == canonical(body) and existing["reviewer_id"] == caller["actor_id"] and existing["proposal_id"] == p["proposal_id"], "IDEMPOTENCY_CONFLICT")
                r.update(approval_id=existing["approval_id"], replayed=True, status=None, data={"decision": s.decision(existing, p, row), "decision_digest": existing["decision_digest"]})
                return True
            require(d is None, "INVALID_STATE")
        elif name == "execute":
            existing = s.one("executions", execution_id=body["execution_id"])
            if existing:
                request = dict(body, actor_id=caller["actor_id"], context_id=caller["context_id"])
                require(existing["request_json"] == canonical(request), "IDEMPOTENCY_CONFLICT")
                result = s.execution(existing, p, d)
                r.update(replayed=True, outcome="committed", status="consumed", effect_status="committed", authorized_at_ms=result["authorized_at_ms"], data={"result": result})
                return True
        elif name == "inspect" and body["kind"] == "execution":
            r.update(status="consumed", authorized_at_ms=e["authorized_at_ms"], effect_status="committed", data={"result": s.execution(e, p, d), "request_digest": e["request_digest"]})
            return True
        return False

    def _proposal_data(self, row, p):
        return dict(proposal=p, proposal_digest=row["proposal_digest"], review={"kind": "approval-review-v1", "proposal": p}, review_digest=row["review_digest"])

    def _propose(self, s, body, caller, ctx, old, now, r):
        policy = self._validate_row("policies", s.one("policies", tenant=ctx["tenant"]))
        tool = self._validate_row("tools", s.one("tools", tool_id="deploy_artifact"))
        reviewer = s.one("actors", actor_id=body["reviewer_id"])
        eligible = s.one("eligibility", tenant=ctx["tenant"], reviewer_id=body["reviewer_id"])
        target = self._validate_row("services", s.one("services", service_id=body["plan"]["steps"][0]["arguments"]["service_id"]))
        require(policy["enabled"] == 1, "POLICY_DISABLED")
        require(reviewer is not None and reviewer["role"] == "reviewer" and eligible is not None and eligible["allowed"] == 1, "REVIEWER_INELIGIBLE")
        self._validate_row("eligibility", eligible)
        require(target["tenant"] == ctx["tenant"] and target["environment"] == ctx["environment"], "TARGET_SCOPE_MISMATCH")
        require(now < body["pending_deadline_ms"] <= min(MAX_INT, now + DAY), "INPUT_INVALID")
        if old:
            previous = s.proposal(old)
            self._reconcile(s, old, previous, s.one("decisions", proposal_id=old["proposal_id"]), now, None)
            require(old["status"] in ("pending", "approved", "superseded") and old["replacement_id"] is None and body["proposal_id"] != old["proposal_id"], "INVALID_STATE")
            if old["status"] != "superseded":
                s.room("transitions", proposal_id=old["proposal_id"])
        s.room("proposals")
        p = {k: body[k] for k in ("schema_version", "proposal_id", "request_id", "context_id", "reviewer_id", "plan", "selected_step_id", "pending_deadline_ms", "grant_ttl_ms", "replaces_proposal_id")}
        p.update({k: ctx[k] for k in ("requester_id", "agent_id", "run_id", "tenant", "environment", "executor_id")})
        p.update(context_revision=ctx["revision"], reviewer_eligibility_revision=eligible["revision"], policy_revision=policy["revision"], tool_id="deploy_artifact", tool_revision=tool["revision"], plan_digest=digest("plan", body["plan"]), target_service_id=target["service_id"], expected_target_revision=target["revision"], prior_artifact_digest=target["artifact_digest"], created_at_ms=now)
        review = dict(kind="approval-review-v1", proposal=p)
        row = dict(proposal_id=p["proposal_id"], request_id=p["request_id"], context_id=p["context_id"], reviewer_id=p["reviewer_id"], target_service_id=p["target_service_id"], canonical_proposal=canonical(p), proposal_digest=digest("proposal", p), canonical_review=canonical(review), review_digest=digest("review", review), submission_json=canonical(body), description=body["description"], status="pending", status_reason=None, replacement_id=None, status_at_ms=now)
        s.insert("proposals", row)
        s.insert("transitions", dict(proposal_id=p["proposal_id"], sequence=1, from_status=None, to_status="pending", reason=None, at_ms=now))
        if old:
            if old["status"] != "superseded":
                s.transition(old, "superseded", "REPLACED", now)
            s.update("proposals", dict(replacement_id=p["proposal_id"]), proposal_id=old["proposal_id"])
        r.update(proposal_id=p["proposal_id"], status="pending", data=self._proposal_data(row, p))

    def _decide(self, s, body, caller, row, p, now, r):
        if row["status"] != "pending":
            raise Failure(row["status_reason"] if row["status"] in ("expired", "superseded") else "INVALID_STATE", r["details"])
        require(body["review_digest"] == row["review_digest"], "BINDING_MISMATCH")
        expiry = add(now, p["grant_ttl_ms"]) if body["decision"] == "approve" else None
        s.room("decisions")
        s.room("transitions", proposal_id=p["proposal_id"])
        d = dict(body, proposal_digest=row["proposal_digest"], reviewer_id=caller["actor_id"], decided_at_ms=now, expires_at_ms=expiry)
        dg = digest("decision", d)
        s.insert("decisions", dict(approval_id=body["approval_id"], proposal_id=p["proposal_id"], canonical_decision=canonical(d), decision_digest=dg, submission_json=canonical(body), reviewer_id=caller["actor_id"], decided_at_ms=now, expires_at_ms=expiry))
        status = "approved" if body["decision"] == "approve" else "rejected"
        s.transition(row, status, None if status == "approved" else "REVIEW_REJECTED", now)
        r.update(approval_id=body["approval_id"], status=status, data={"decision": d, "decision_digest": dg})

    def _read(self, s, name, body, row, p, d, e, r):
        r["details"] = []
        if name == "review":
            r["data"] = {"review": {"kind": "approval-review-v1", "proposal": p}, "review_digest": row["review_digest"], "description": row["description"]}
        elif body["kind"] == "proposal":
            transitions = s.all("transitions", proposal_id=p["proposal_id"])
            transitions.sort(key=lambda h: h["sequence"])
            r["data"] = dict(self._proposal_data(row, p), description=row["description"], transitions=transitions)
        else:
            r["data"] = {"proposal_id": p["proposal_id"], "decision": s.decision(d, p, row), "decision_digest": d["decision_digest"]}

    def _reconcile(self, s, row, p, d, now, r):
        if row["status"] not in ("pending", "approved"):
            return
        deadline = p["pending_deadline_ms"] if row["status"] == "pending" else d["expires_at_ms"]
        reason, detail = None, []
        if now >= deadline:
            reason = "PENDING_EXPIRED" if row["status"] == "pending" else "GRANT_EXPIRED"
        else:
            ctx = self._validate_row("contexts", s.one("contexts", context_id=p["context_id"]))
            tool = self._validate_row("tools", s.one("tools", tool_id=p["tool_id"]))
            policy = self._validate_row("policies", s.one("policies", tenant=p["tenant"]))
            eligible = self._validate_row("eligibility", s.one("eligibility", tenant=p["tenant"], reviewer_id=p["reviewer_id"]))
            target = self._validate_row("services", s.one("services", service_id=p["target_service_id"]))
            candidates = [
                (ctx["revision"] != p["context_revision"] or any(ctx[k] != p[k] for k in ("requester_id", "agent_id", "run_id", "tenant", "environment", "executor_id")), "CONTEXT_CHANGED", "/context", p["context_revision"], ctx["revision"]),
                (tool["revision"] != p["tool_revision"], "TOOL_CHANGED", "/tool", p["tool_revision"], tool["revision"]),
                (policy["revision"] != p["policy_revision"] or not policy["enabled"], "POLICY_CHANGED", "/policy", {"revision": p["policy_revision"], "enabled": True} if not policy["enabled"] else p["policy_revision"], {"revision": policy["revision"], "enabled": False} if not policy["enabled"] else policy["revision"]),
                (eligible["revision"] != p["reviewer_eligibility_revision"] or not eligible["allowed"], "REVIEWER_CHANGED", "/eligibility", {"revision": p["reviewer_eligibility_revision"], "allowed": True} if not eligible["allowed"] else p["reviewer_eligibility_revision"], {"revision": eligible["revision"], "allowed": False} if not eligible["allowed"] else eligible["revision"]),
                (target["revision"] != p["expected_target_revision"] or target["artifact_digest"] != p["prior_artifact_digest"] or target["tenant"] != p["tenant"] or target["environment"] != p["environment"], "TARGET_REVISION_CHANGED", "/target", p["expected_target_revision"], target["revision"]),
            ]
            for changed, code, path, expected, actual in candidates:
                if changed:
                    reason = code
                    detail = [{"path": path, "expected": canonical(expected), "actual": canonical(actual)}]
                    break
        if reason:
            s.transition(row, "expired" if reason.endswith("EXPIRED") else "superseded", reason, now)
            if r is not None:
                r["status"] = row["status"]
                r["details"] = detail

    def _execute(self, s, body, caller, row, p, d, now, r):
        status = row["status"]
        if status != "approved":
            raise Failure({"pending": "APPROVAL_PENDING", "consumed": "APPROVAL_CONSUMED", "revoked": "APPROVAL_REVOKED", "rejected": "REVIEW_REJECTED"}.get(status, row["status_reason"]), r["details"])
        expected = {"proposal_id": p["proposal_id"], "proposal_digest": row["proposal_digest"], "review_digest": row["review_digest"], "binding": p}
        mismatches = v.differences(expected, body["intent"])
        if mismatches:
            raise Failure("BINDING_MISMATCH", sorted(mismatches, key=lambda x: (x["path"], x["expected"], x["actual"])))
        s.room("executions")
        s.room("transitions", proposal_id=p["proposal_id"])
        after = add(p["expected_target_revision"], 1)
        self._point("after_checks")
        from .deployment import deploy
        result = deploy(s, p, d["approval_id"], body["execution_id"], now, after)
        request = dict(body, actor_id=caller["actor_id"], context_id=caller["context_id"])
        s.insert("executions", dict(execution_id=body["execution_id"], approval_id=d["approval_id"], proposal_id=p["proposal_id"], requester_id=caller["actor_id"], context_id=caller["context_id"], request_json=canonical(request), request_digest=digest("execution", request), result_json=canonical(result), authorized_at_ms=now, before_revision=p["expected_target_revision"], after_revision=after))
        s.transition(row, "consumed", None, now)
        s.proposal(row)
        r.update(status="consumed", outcome="committed", effect_status="committed", authorized_at_ms=now, data={"result": result})

    def _revoke(self, s, row, now, r):
        status = row["status"]
        require(status in ("approved", "revoked"), "TOO_LATE" if status == "consumed" else "APPROVAL_PENDING" if status == "pending" else "INVALID_STATE")
        if status == "approved":
            s.transition(row, "revoked", None, now)
        r.update(status="revoked", data={"changed": status == "approved"})

    def _admin(self, s, body, r):
        kind = body["kind"]
        table = {"service": "services", "context": "contexts", "tool": "tools", "policy": "policies", "eligibility": "eligibility"}[kind]
        key = {"service": "service_id", "context": "context_id", "tool": "tool_id", "policy": "tenant", "eligibility": "tenant"}[kind]
        where = {key: body["id"]}
        if kind == "eligibility":
            where["reviewer_id"] = body["reviewer_id"]
        row = s.one(table, **where)
        require(row is not None, "NOT_FOUND")
        self._validate_row(table, row)
        require(row["revision"] == body["expected_revision"], "REVISION_CONFLICT")
        revision = add(row["revision"], 1)
        changes = {k: int(x) if type(x) is bool else x for k, x in body["changes"].items()}
        changes["revision"] = revision
        require(s.update(table, changes, **where, revision=row["revision"]) == 1, "REVISION_CONFLICT")
        r["data"] = dict(kind=kind, id=body["id"], reviewer_id=body.get("reviewer_id"), revision=revision)

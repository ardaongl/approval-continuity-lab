"""Fixed, offline experiments with durable independent assertions."""
import copy
import json
from pathlib import Path
import tempfile
from .canonical import canonical
from .mediator import Lab
from .models import Failure
from .observations import check, snapshot
from .processes import Worker
from .report import report, serialize
from .resources import asset, bytes_asset
from .scenario_worker import FixedClock
from .validation import decode

IDS = tuple("D%02d" % n for n in range(1, 15))
EXPLANATIONS = (
    "exact reviewed deployment committed once",
    "changed submitted bindings do not consume approval",
    "strict input bytes have explicit canonical meaning",
    "validity uses final authorization time and durable floor",
    "committed retry retrieves history without another effect",
    "serialized competing executions commit one effect",
    "revocation cannot undo a committed deployment",
    "target revision drift requires a fresh review",
    "current trusted revisions must still match review",
    "crash recovery distinguishes rollback from committed history",
    "trusted review renders stored executable bindings",
    "missing authoritative state never implies approval",
    "unsafe educational baseline reuses approval after drift",
    "uncontrolled downstream file is outside guarantee",
)
AGENT = {"actor_id": "req_a", "context_id": "c1"}
REVIEWER = {"actor_id": "rev_a", "context_id": None}
OPERATOR = {"actor_id": "op", "context_id": None}
A, B, C = ("sha256:" + c * 64 for c in "abc")


def expect(value, code="OK"):
    check(value["code"] == code)
    return value


class Fixture:
    def __init__(self, directory, name, approved=True):
        self.path = directory / (name + ".sqlite")
        self.clock = FixedClock(1000)
        self.lab = Lab.open(self.path, self.clock)
        expect(self.lab.initialize(asset("base-config.json"), OPERATOR))
        expect(self.lab.propose(asset("submission.json"), AGENT))
        if approved:
            self.clock.now = 1500
            expect(self.lab.decide(asset("decision-input.json"), REVIEWER))
        self.clock.now = 1600

    def execute(self, code="OK", body=None):
        return expect(self.lab.execute(body or asset("execution-input.json"), AGENT), code)

    def admin(self, kind="service", id="svc1", expected=1, changes=None, now=1550):
        self.clock.now = now
        default = {"service": {"artifact_digest": C}, "context": {"executor_id": "ex3"}, "tool": {}, "policy": {"enabled": False}, "eligibility": {"allowed": False}}
        body = dict(schema_version=1, kind=kind, id=id, expected_revision=expected, changes=default[kind] if changes is None else changes)
        if kind == "eligibility":
            body["reviewer_id"] = "rev_a"
        expect(self.lab.admin_update(body, OPERATOR))
        self.clock.now = 1600

    def observe(self, step, result, status, effects, revision, artifact=None):
        state = snapshot(self.path)
        check(state["proposals"][0]["status"] == status)
        check(len(state["executions"]) == effects and state["services"][0]["revision"] == revision)
        if artifact is not None:
            check(state["services"][0]["artifact_digest"] == artifact)
        return dict(step=step, code=result["code"], status=status, effect_count=effects, service_revision=revision)


def experiment(id, directory):
    observations = []
    if id == "D01":
        f = Fixture(directory, "exact")
        r = f.execute()
        check(serialize(r) == bytes_asset("d01-report.golden.json"))
        state = snapshot(f.path)
        check(all(s["revision"] == 1 and s["artifact_digest"] == A for s in state["services"][1:]))
        observations.append(f.observe("execute", r, "consumed", 1, 2, B))
    elif id == "D02":
        variants = []
        p = asset("proposal.expected.json")
        for key, value in p.items():
            if key in ("schema_version", "tool_id", "plan"):
                continue
            new = value + 1 if type(value) is int else "p2" if value is None else "0" * 64 if key.endswith("_digest") and key != "prior_artifact_digest" else C if key == "prior_artifact_digest" else value + "x"
            variants.append((["binding", key], new))
        variants.extend([(["binding", "plan", "revision"], 2), (["binding", "plan", "steps", 0, "step_id"], "s2"), (["binding", "plan", "steps", 0, "arguments", "artifact_digest"], C), (["binding", "plan", "steps", 0, "arguments", "service_id"], "svc2"), (["review_digest"], "0" * 64), (["proposal_digest"], "0" * 64), (["proposal_id"], "p2")])
        f = Fixture(directory, "mutations")
        immutable = snapshot(f.path)["decisions"]
        for i, (path, value) in enumerate(variants):
            body = asset("execution-input.json")
            cursor = body["intent"]
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            r = f.execute("BINDING_MISMATCH", body)
            check(snapshot(f.path)["decisions"] == immutable)
            observations.append(f.observe("mutation-%02d" % i, r, "approved", 0, 1, A))
        for context in ({"actor_id": "req_b", "context_id": "c2"}, {"actor_id": "req_a", "context_id": "c3"}):
            expect(f.lab.execute(asset("execution-input.json"), context), "CALLER_MISMATCH")
        body = asset("execution-input.json")
        body["intent"]["binding"]["plan"]["steps"] *= 2
        f.execute("INPUT_INVALID", body)
        observations.append(f.observe("correct-retry", f.execute(), "consumed", 1, 2, B))
    elif id == "D03":
        f = Fixture(directory, "parsing")
        initial = snapshot(f.path)
        for vector in asset("canonical-vectors.json"):
            check(canonical(decode(vector["input"].encode())) == vector["canonical_ascii"])
        negatives = [bytes_asset("duplicate-key.input.txt"), b'{"nested":{"k":1,"k":1}}', b'1.0', b'1e0', b'NaN', b'Infinity', b'\xef\xbb\xbf{}', b'\xff', b'"\\ud800"', b'9007199254740992', b'[' * 17 + b'0' + b']' * 17, b' ' * 65537]
        for raw in negatives:
            try:
                decode(raw)
            except Failure as exc:
                check(exc.code in ("INPUT_INVALID", "INPUT_LIMIT"))
            else:
                check(False)
        for key, value in (("reason", None), ("reason", ""), ("reason", "\0"), ("reason", "\ud800"), ("reason", "é" * 512 + "a"), ("schema_version", True), ("schema_version", 2), ("extra", 1)):
            body = asset("decision-input.json")
            body[key] = value
            expect(f.lab.decide(body, REVIEWER), "UNSUPPORTED_VERSION" if key == "schema_version" and type(value) is int and value == 2 else "INPUT_INVALID")
        check(snapshot(f.path) == initial)
        observations.append(f.observe("strict-invalid-input", {"code": "INPUT_INVALID"}, "approved", 0, 1, A))
    elif id == "D04":
        for approved, times in ((False, (1999, 2000, 2001)), (True, (2499, 2500, 2501))):
            for time in times:
                f = Fixture(directory, str(time), approved)
                f.clock.now = time
                code = "OK" if time == times[0] else "GRANT_EXPIRED" if approved else "PENDING_EXPIRED"
                r = f.execute(code) if approved else expect(f.lab.decide(asset("decision-input.json"), REVIEWER), code)
                observations.append(f.observe(str(time), r, ("consumed" if approved else "approved") if code == "OK" else "expired", int(approved and code == "OK"), 2 if approved and code == "OK" else 1))
        f = Fixture(directory, "floor")
        f.clock.now = 2400
        expect(f.lab.inspect("proposal", "p1", AGENT))
        state = snapshot(f.path)
        f.clock.now = 2399
        f.lab = Lab.open(f.path, f.clock)
        r = f.execute("CLOCK_REGRESSION")
        check(snapshot(f.path) == state)
        observations.append(f.observe("backward-restart", r, "approved", 0, 1))
    elif id == "D05":
        f = Fixture(directory, "retry")
        first = f.execute()
        f.admin(expected=2, now=1700)
        state = snapshot(f.path)
        f.clock.now = 0
        r = f.execute()
        check(r["replayed"] and r["data"]["result"] == first["data"]["result"] and snapshot(f.path) == state)
        observations.append(f.observe("historical-retry", r, "consumed", 1, 3, C))
    elif id in ("D06", "D07", "D08"):
        if id == "D06":
            schedules = [("execute-a", "execute-b", "APPROVAL_CONSUMED", "consumed", 1), ("execute-b", "execute-a", "APPROVAL_CONSUMED", "consumed", 1), ("execute-same", "execute-same", "OK", "consumed", 1)]
        elif id == "D07":
            schedules = [("revoke-before", "execute-a", "APPROVAL_REVOKED", "revoked", 0), ("execute-a", "revoke-after", "TOO_LATE", "consumed", 1)]
        else:
            schedules = [("target-before", "execute-a", "TARGET_REVISION_CHANGED", "superseded", 0), ("execute-a", "target-after", "REVISION_CONFLICT", "consumed", 1)]
        for i, (first, second, code, status, count) in enumerate(schedules):
            f = Fixture(directory, "schedule%d" % i)
            with Worker(f.path, first) as a, Worker(f.path, second) as b:
                a.reach("before_begin")
                b.reach("before_begin")
                a.release()
                a.reach("after_begin")
                b.release()
                expect(a.finish())
                r = expect(b.finish(), code)
            observations.append(f.observe("schedule%d" % i, r, status, count, 1 if id == "D07" and i == 0 else 2))
        if id == "D06":
            f = Fixture(directory, "busy")
            with Worker(f.path, "execute-a") as a:
                a.reach("after_begin")
                with Worker(f.path, "execute-b") as b:
                    expect(b.finish(), "STORAGE_BUSY")
                expect(a.finish())
            with Worker(f.path, "execute-b") as b:
                r = expect(b.finish(), "APPROVAL_CONSUMED")
            observations.append(f.observe("explicit-retry-after-busy", r, "consumed", 1, 2, B))
        if id == "D07":
            f = Fixture(directory, "repeat-revoke")
            expect(f.lab.revoke({"schema_version": 1, "proposal_id": "p1"}, REVIEWER))
            state = snapshot(f.path)
            repeated = expect(f.lab.revoke({"schema_version": 1, "proposal_id": "p1"}, REVIEWER))
            check(not repeated["data"]["changed"] and snapshot(f.path) == state)
            observations.append(f.observe("repeated-revoke", repeated, "revoked", 0, 1, A))
        if id == "D08":
            f = Fixture(directory, "aba")
            f.admin()
            f.admin(expected=2, changes={"artifact_digest": A}, now=1575)
            r = f.execute("TARGET_REVISION_CHANGED")
            observations.append(f.observe("aba", r, "superseded", 0, 3, A))
    elif id == "D09":
        for i, (kind, key, code) in enumerate((("tool", "deploy_artifact", "TOOL_CHANGED"), ("context", "c1", "CONTEXT_CHANGED"), ("policy", "t1", "POLICY_CHANGED"), ("eligibility", "t1", "REVIEWER_CHANGED"))):
            f = Fixture(directory, str(i))
            f.admin(kind, key)
            observations.append(f.observe(kind, f.execute(code), "superseded", 0, 1, A))
    elif id == "D10":
        for i, point in enumerate(("before_commit", "after_commit_before_response")):
            f = Fixture(directory, "crash%d" % i)
            with Worker(f.path, "execute-same") as worker:
                worker.reach(point)
                before = snapshot(f.path)
                check(before["proposals"][0]["status"] == ("approved" if i == 0 else "consumed") and len(before["executions"]) == i and before["services"][0]["revision"] == 1 + i and before["meta"][0]["observed_time_floor_ms"] == (1500 if i == 0 else 1600))
                worker.kill()
            check(snapshot(f.path) == before)
            f.lab = Lab.open(f.path, f.clock)
            r = f.execute()
            check(r["replayed"] == bool(i))
            observations.append(f.observe(point, r, "consumed", 1, 2, B))
    elif id == "D11":
        f = Fixture(directory, "review", False)
        r = expect(f.lab.review("p1", REVIEWER))
        check(r["data"]["review"] == asset("review.expected.json"))
        from .review import render
        check(render(r["data"]["review"], r["data"]["description"]).encode() == bytes_asset("review-suffix.golden.txt"))
        wrong = asset("decision-input.json")
        wrong["review_digest"] = "0" * 64
        r = expect(f.lab.decide(wrong, REVIEWER), "BINDING_MISMATCH")
        observations.append(f.observe("forged-digest", r, "pending", 0, 1, A))
    elif id == "D12":
        clock = FixedClock(1600)
        path = directory / "absent.sqlite"
        expect(Lab.open(path, clock).execute(asset("execution-input.json"), AGENT), "STORAGE_ERROR")
        check(not path.exists())
        path.write_bytes(b"not a database")
        expect(Lab.open(path, clock).execute(asset("execution-input.json"), AGENT), "STATE_CORRUPT")
        observations.append(dict(step="unavailable-state", code="STATE_CORRUPT", status=None, effect_count=0, service_revision=None))
    elif id == "D13":
        from .naive import educational_d13
        reference, naive = Fixture(directory, "reference"), Fixture(directory, "naive")
        reference.admin()
        naive.admin()
        r = reference.execute("TARGET_REVISION_CHANGED")
        observations.append(reference.observe("reference-refusal", r, "superseded", 0, 2, C))
        educational_d13(naive.path)
        state = snapshot(naive.path)
        check(state["proposals"][0]["status"] == "approved" and not state["executions"] and state["services"][0]["artifact_digest"] == B and state["services"][0]["revision"] == 3)
        observations.append(dict(step="naive-NAIVE_BASELINE-UNSAFE_EDUCATIONAL", code="OK", status="approved", effect_count=1, service_revision=3))
    elif id == "D14":
        f = Fixture(directory, "outside")
        sentinel = directory / "outside-effect.json"
        sentinel.write_bytes(b'{"artifact_digest":"sha256:' + b'a' * 64 + b'"}\n')
        check(json.loads(sentinel.read_bytes()) == {"artifact_digest": A})
        r = f.execute()
        observations.append(f.observe("reference-execute", r, "consumed", 1, 2, B))
        sentinel.write_bytes(b'{"artifact_digest":"sha256:' + b'c' * 64 + b'"}\n')
        check(json.loads(sentinel.read_bytes()) == {"artifact_digest": C} and "outside-effect.json" not in canonical(r["data"]))
        observations.append(dict(step="outside-file", code="OK", status=None, effect_count=None, service_revision=None))
    return observations


def dispatch(command, selected=None):
    if command == "scenario-list":
        return report(command, mode="SCENARIO", data={"scenarios": list(IDS)})
    summaries = []
    for id in IDS if selected == "all" else (selected,):
        summary = dict(scenario_id=id, classification="COMPARISON" if id == "D13" else "OUTSIDE_GUARANTEE" if id == "D14" else "REFERENCE", verified=False, observations=[], explanation=EXPLANATIONS[IDS.index(id)])
        try:
            with tempfile.TemporaryDirectory(prefix="acl-") as temp:
                summary["observations"] = experiment(id, Path(temp))
            summary["verified"] = True
        except Exception:
            summaries.append(summary)
            return report(command, mode="SCENARIO", outcome="error", code="SCENARIO_FAILED", data={"scenarios": summaries})
        summaries.append(summary)
    return report(command, mode="SCENARIO", outcome="verified", data={"scenarios": summaries})

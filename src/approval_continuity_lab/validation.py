"""Bounded strict JSON and schema-1 shape validation; no database access."""
import json
import re
from .canonical import canonical
from .models import Failure, MAX_INT, DAY


def invalid(path="/", label="valid UTF-8 JSON", value="invalid", missing=False):
    actual = "missing" if missing else canonical(value)
    if label == "valid UTF-8 JSON":
        actual = "invalid"
    if len(actual.encode("utf-8")) > 4096:
        actual = "oversize"
    raise Failure("INPUT_INVALID", [{"path": path or "/", "expected": label, "actual": actual}])


def decode(raw):
    if not isinstance(raw, bytes):
        invalid()
    if len(raw) > 65536:
        raise Failure("INPUT_LIMIT")
    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            invalid()
        depth, quoted, escaped = 0, False, False
        for ch in text:
            if quoted:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    quoted = False
            elif ch == '"':
                quoted = True
            elif ch in "[{":
                depth += 1
                if depth > 16:
                    raise Failure("INPUT_LIMIT")
            elif ch in "]}":
                depth -= 1

        def pairs(items):
            obj = {}
            for k, v in items:
                if k in obj:
                    invalid()
                obj[k] = v
            return obj

        def no_number(_):
            invalid()

        value = json.loads(text, object_pairs_hook=pairs, parse_float=no_number,
                           parse_constant=no_number)
        generic(value)
        return value
    except (UnicodeError, ValueError, RecursionError):
        invalid()


def generic(value, depth=0):
    if isinstance(value, (dict, list)):
        if depth >= 16:
            raise Failure("INPUT_LIMIT")
        if isinstance(value, dict):
            if not all(isinstance(k, str) for k in value):
                invalid()
            for k in sorted(value):
                generic(k, depth + 1)
                generic(value[k], depth + 1)
        else:
            for v in value:
                generic(v, depth + 1)
    elif isinstance(value, str):
        if "\0" in value or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            invalid()
    elif type(value) is int:
        if not 0 <= value <= MAX_INT:
            invalid()
    elif value is not None and type(value) is not bool:
        invalid()


def pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def obj(value, fields, path=""):
    if type(value) is not dict:
        invalid(path, "object", value)
    for key in sorted(set(value) | set(fields)):
        p = pointer(path, key)
        if key not in fields:
            invalid(p, "no unknown fields", value[key])
        if key not in value:
            invalid(p, "required field", missing=True)
        check(value[key], fields[key], p)


def check(v, rule, path):
    if isinstance(rule, dict):
        obj(v, rule, path)
        return
    if isinstance(rule, tuple):
        if v not in rule or type(v) is not type(rule[0]):
            invalid(path, "supported value", v)
        return
    if rule == "version":
        if type(v) is not int:
            invalid(path, "schema version integer", v)
        if v != 1:
            raise Failure("UNSUPPORTED_VERSION")
        return
    if rule in ("int", "rev", "ttl"):
        low = 0 if rule == "int" else 1
        high = DAY if rule == "ttl" else MAX_INT
        if type(v) is not int or not low <= v <= high:
            invalid(path, rule, v)
    elif rule == "bool":
        if type(v) is not bool:
            invalid(path, "boolean", v)
    elif rule == "id?" and v is None:
        return
    elif rule in ("id", "id?"):
        if not isinstance(v, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", v):
            invalid(path, "ASCII identifier", v)
    elif rule in ("hex", "artifact"):
        pattern = ("sha256:" if rule == "artifact" else "") + "[0-9a-f]{64}"
        if not isinstance(v, str) or not re.fullmatch(pattern, v):
            invalid(path, rule, v)
    elif rule in ("reason", "description", "display_name"):
        lo, hi = {"reason": (1, 1024), "description": (0, 4096), "display_name": (0, 128)}[rule]
        if not isinstance(v, str) or not lo <= len(v.encode("utf-8")) <= hi:
            invalid(path, rule + " UTF-8 bytes", v)
    elif rule == "steps":
        if type(v) is not list or len(v) != 1:
            invalid(path, "one effectful step", v)
        obj(v[0], STEP, pointer(path, 0))
    else:
        if rule not in ("int", "rev", "ttl", "bool", "id", "id?", "hex", "artifact", "reason", "description", "display_name"):
            raise ValueError("Unknown schema rule")


STEP = {"step_id": "id", "tool_id": ("deploy_artifact",),
        "arguments": {"service_id": "id", "artifact_digest": "artifact"}}
PLAN = {"revision": "rev", "steps": "steps"}
SUBMISSION = dict.fromkeys("proposal_id request_id context_id reviewer_id selected_step_id".split(), "id")
SUBMISSION.update(schema_version="version", plan=PLAN, pending_deadline_ms="int",
                  grant_ttl_ms="ttl", description="description", replaces_proposal_id="id?")
PROPOSAL = dict.fromkeys("proposal_id request_id context_id requester_id agent_id run_id tenant environment executor_id reviewer_id selected_step_id target_service_id".split(), "id")
PROPOSAL.update(dict.fromkeys("context_revision reviewer_eligibility_revision policy_revision tool_revision expected_target_revision".split(), "rev"))
PROPOSAL.update(schema_version="version", tool_id=("deploy_artifact",), plan=PLAN,
                plan_digest="hex", prior_artifact_digest="artifact", created_at_ms="int",
                pending_deadline_ms="int", grant_ttl_ms="ttl", replaces_proposal_id="id?")
DECIDE = {"schema_version": "version", "approval_id": "id", "proposal_id": "id",
          "review_digest": "hex", "decision": ("approve", "reject"), "reason": "reason"}
EXECUTE = {"schema_version": "version", "execution_id": "id", "approval_id": "id",
           "intent": {"proposal_id": "id", "proposal_digest": "hex", "review_digest": "hex", "binding": PROPOSAL}}
CONFIG_ROWS = {
    "actors": {"actor_id": "id", "role": ("operator", "agent", "reviewer")},
    "contexts": dict(dict.fromkeys("context_id requester_id agent_id run_id tenant environment executor_id".split(), "id"), revision="rev"),
    "tools": {"tool_id": ("deploy_artifact",), "revision": "rev"},
    "policies": {"tenant": "id", "revision": "rev", "enabled": "bool"},
    "eligibility": {"tenant": "id", "reviewer_id": "id", "revision": "rev", "allowed": "bool"},
    "services": dict(dict.fromkeys("service_id tenant environment".split(), "id"), revision="rev", display_name="display_name", artifact_digest="artifact"),
}


def config(value):
    if type(value) is not dict:
        invalid("/", "config object", value)
    keys = set(CONFIG_ROWS) | {"schema_version"}
    for k in sorted(set(value) | keys):
        if k not in keys or k not in value:
            invalid(pointer("", k), "required config field", value.get(k), k not in value)
        if k == "schema_version":
            check(value[k], "version", "/schema_version")
            continue
        rows = value[k]
        if type(rows) is not list or len(rows) > (1 if k == "tools" else 256):
            invalid("/" + k, "bounded row list", rows)
        seen = set()
        for i, row in enumerate(rows):
            path = pointer("/" + k, i)
            obj(row, CONFIG_ROWS[k], path)
            key = (row["tenant"], row["reviewer_id"]) if k == "eligibility" else row[next(iter(CONFIG_ROWS[k]))]
            if key in seen:
                invalid(path, "unique row identity", row)
            seen.add(key)
    if len(value["tools"]) != 1:
        invalid("/tools", "one tool", value["tools"])
    actors = {r["actor_id"]: r["role"] for r in value["actors"]}
    tenants = {r["tenant"] for r in value["policies"]}
    for row in value["contexts"]:
        if actors.get(row["requester_id"]) != "agent" or row["tenant"] not in tenants:
            invalid("/contexts", "valid context dependencies", row)
    for row in value["eligibility"]:
        if actors.get(row["reviewer_id"]) != "reviewer" or row["tenant"] not in tenants:
            invalid("/eligibility", "valid reviewer and policy", row)


def validate(command, value):
    generic(value)
    # Decoded mappings use compact UTF-8 for their size bound. C's ASCII
    # escapes can be longer than the actual valid UTF-8 input on the wire.
    if len(json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")) > 65536:
        raise Failure("INPUT_LIMIT")
    if command == "init":
        config(value)
    elif command == "admin-update":
        if type(value) is not dict or value.get("kind") not in ("service", "context", "tool", "policy", "eligibility"):
            invalid("/kind", "supported admin kind", value.get("kind") if isinstance(value, dict) else value)
        kind = value["kind"]
        changes = {"service": {"artifact_digest": "artifact"}, "context": {"executor_id": "id"}, "tool": {}, "policy": {"enabled": "bool"}, "eligibility": {"allowed": "bool"}}[kind]
        fields = {"schema_version": "version", "kind": (kind,), "id": ("deploy_artifact",) if kind == "tool" else "id", "expected_revision": "rev", "changes": changes}
        if kind == "eligibility":
            fields["reviewer_id"] = "id"
        obj(value, fields)
    else:
        fields = {"propose": SUBMISSION, "decide": DECIDE, "execute": EXECUTE,
                  "revoke": {"schema_version": "version", "proposal_id": "id"},
                  "review": {"proposal_id": "id"},
                  "inspect": {"kind": ("proposal", "approval", "execution"), "id": "id"}}[command]
        obj(value, fields)
    if command == "propose" and value["selected_step_id"] != value["plan"]["steps"][0]["step_id"]:
        invalid("/selected_step_id", "selected sole step", value["selected_step_id"])


def differences(expected, actual, path=""):
    result = []
    if type(expected) is type(actual) is dict:
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected or key not in actual:
                result.append({"path": pointer(path, key), "expected": canonical(expected.get(key)), "actual": canonical(actual.get(key))})
            else:
                result.extend(differences(expected[key], actual[key], pointer(path, key)))
    elif type(expected) is type(actual) is list and len(expected) == len(actual):
        for i, (a, b) in enumerate(zip(expected, actual)):
            result.extend(differences(a, b, pointer(path, i)))
    elif type(expected) is not type(actual) or expected != actual:
        result.append({"path": path or "/", "expected": canonical(expected), "actual": canonical(actual)})
    if len(result) > 256:
        raise Failure("INPUT_LIMIT")
    for entry in result:
        for key in ("expected", "actual"):
            if len(entry[key].encode()) > 4096:
                entry[key] = "oversize"
    return result

"""Deterministic report snapshots and serialization, without IO."""
from .canonical import canonical
from .models import EXITS, Failure, MAX_REPORT
from .review import render


def report(command, **values):
    r = dict(schema_version=1, command=command, mode="REFERENCE", outcome="ok", code="OK",
             proposal_id=None, approval_id=None, execution_id=None, status=None,
             observed_at_ms=None, authorized_at_ms=None, replayed=False, effect_status="none", details=[], data=None)
    r.update(values)
    return r


def set_error(r, code, details=None):
    r.update(code=code, outcome="denied" if EXITS[code] == 3 else "interrupted" if code == "INTERRUPTED" else "error", details=details or [], data=None)
    return r


def serialize(r, format="json"):
    if format == "json":
        text = canonical(r) + "\n"
    else:
        number = lambda x: "none" if x is None else str(x)
        text = (f'COMMAND: {r["command"]} | MODE: {r["mode"]}\n'
                f'OUTCOME: {r["outcome"]} | CODE: {r["code"]}\n'
                f'EXPLANATION: {r["code"].lower().replace("_", " ")}\n'
                f'STATUS: {r["status"] or "none"} | EFFECT: {r["effect_status"]} | REPLAYED: {str(r["replayed"]).lower()}\n'
                f'OBSERVED_AT_MS: {number(r["observed_at_ms"])} | AUTHORIZED_AT_MS: {number(r["authorized_at_ms"])}\n')
        for d in r["details"]:
            text += "DETAIL " + canonical(d["path"]) + ": expected=" + canonical(d["expected"]) + " actual=" + canonical(d["actual"]) + "\n"
        text += "DATA: " + canonical(r["data"]) + "\n"
        if r["command"] == "review" and r["data"]:
            text += render(r["data"]["review"], r["data"]["description"])
    encoded = text.encode("ascii")
    if len(encoded) > MAX_REPORT:
        raise Failure("INTERNAL_ERROR")
    return encoded

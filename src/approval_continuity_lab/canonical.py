"""Canonical representation of already validated values (contract C and H)."""
import hashlib
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def digest(domain, value):
    return hashlib.sha256(("ACL/v1/" + domain + "\0" + canonical(value)).encode("ascii")).hexdigest()

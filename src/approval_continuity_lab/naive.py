"""Intentionally unsafe fixed D13 negative control; not a public execute mode."""
from .models import require, add
from .store import Store


def educational_d13(path):
    store = Store(path)
    try:
        store.connect()
        store.begin()
        # Deliberately ignores expiry/drift/replay and leaves approval unchanged.
        decision = store.one("decisions", approval_id="a1")
        require(decision is not None, "INVALID_STATE")
        proposal = store.one("proposals", proposal_id="p1")
        require(proposal["status"] == "approved", "INVALID_STATE")
        target = store.one("services", service_id="svc1")
        store.update("services", dict(artifact_digest="sha256:" + "b" * 64, revision=add(target["revision"], 1)), service_id="svc1")
        store.commit()
    finally:
        store.rollback()
        store.close()

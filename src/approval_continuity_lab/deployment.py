"""One simulated service update, always using the caller's transaction."""
from .models import require


def deploy(store, p, approval_id, execution_id, now, after):
    artifact = p["plan"]["steps"][0]["arguments"]["artifact_digest"]
    changed = store.update("services", dict(artifact_digest=artifact, revision=after), service_id=p["target_service_id"], revision=p["expected_target_revision"])
    require(changed == 1, "STATE_CORRUPT")
    return dict(approval_id=approval_id, execution_id=execution_id, proposal_id=p["proposal_id"], service_id=p["target_service_id"], tenant=p["tenant"], environment=p["environment"], artifact_digest=artifact, before_revision=p["expected_target_revision"], after_revision=after, authorized_at_ms=now)

"""Optional evidence capture enabled only by test-run orchestration."""
import json
import os
from pathlib import Path


def _sql_value(value):
    if isinstance(value, bytes):
        return {"sqlite_blob_hex": value.hex()}
    raise TypeError("Unsupported evidence value: " + type(value).__name__)


def save(name, value):
    directory = os.environ.get("ACL_TEST_EVIDENCE")
    if directory:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        file = target / (name + ".json")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(value, sort_keys=True, indent=2, default=_sql_value))

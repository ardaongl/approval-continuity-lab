"""Run one check and retain exact command, exit, environment and candidate hashes."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
import os


def main():
    name, *argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv.pop(0)
    root = Path(__file__).resolve().parents[1]
    ignored = {".git", ".venv", ".local-verification", "dist", "build", "__pycache__"}
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob("*")) if p.is_file()
              and not any(x in ignored or x.endswith(".egg-info") for x in p.relative_to(root).parts)}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = root / ".local-verification" / "build" / (stamp + "-" + name)
    evidence.mkdir(parents=True)
    result = subprocess.run(argv, cwd=root, capture_output=True)
    (evidence / "stdout.txt").write_bytes(result.stdout)
    (evidence / "stderr.txt").write_bytes(result.stderr)
    record = dict(command=argv, exit_code=result.returncode, timestamp_utc=stamp,
                  executable=sys.executable, python=sys.version, sqlite=sqlite3.sqlite_version,
                  os=platform.platform(), fingerprint=hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), files=hashes)
    record['test_environment'] = {key: os.environ.get(key) for key in ('ACL_TEST_EVIDENCE','ACL_WHEELHOUSE','PIP_NO_INDEX','PYTHONDONTWRITEBYTECODE')}
    (evidence / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    sys.stdout.buffer.write(result.stdout)
    sys.stderr.buffer.write(result.stderr)
    print("EVIDENCE:", evidence)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

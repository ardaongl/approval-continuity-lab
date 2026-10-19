"""Private fixed-role subprocesses for built-in experiments; no dynamic code."""
import argparse
import os
import select
import sys
from .canonical import canonical
from .mediator import Lab
from .models import EXITS
from .report import serialize


class FixedClock:
    def __init__(self, now):
        self.now = now

    def now_ms(self):
        return self.now


class PipeObserver:
    def __init__(self, ready, release):
        self.ready, self.release = ready, release

    def reached(self, point):
        os.write(self.ready, (point + "\n").encode("ascii"))
        if not select.select([self.release], [], [], 5)[0] or os.read(self.release, 1) != b"+":
            raise RuntimeError("Coordinator rendezvous failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--role", required=True, choices=("execute-a", "execute-b", "execute-same", "revoke-before", "revoke-after", "target-before", "target-after"))
    parser.add_argument("--ready-fd", required=True, type=int)
    parser.add_argument("--release-fd", required=True, type=int)
    args = parser.parse_args()
    # Imports/resources are used only after explicit worker entrypoint.
    from .resources import asset
    observer = PipeObserver(args.ready_fd, args.release_fd)
    role = args.role
    now = 1550 if role.endswith("before") else 1700 if role.endswith("after") else 1600
    with Lab.open(args.db, FixedClock(now), observer) as lab:
        if role.startswith("execute"):
            body = asset("execution-input.json")
            body["execution_id"] = "x1" if role == "execute-same" else "x-a" if role == "execute-a" else "x-b"
            r = lab.execute(body, {"actor_id": "req_a", "context_id": "c1"})
        elif role.startswith("revoke"):
            r = lab.revoke({"schema_version": 1, "proposal_id": "p1"}, {"actor_id": "rev_a", "context_id": None})
        else:
            r = lab.admin_update({"schema_version": 1, "kind": "service", "id": "svc1", "expected_revision": 1, "changes": {"artifact_digest": "sha256:" + "c" * 64}}, {"actor_id": "op", "context_id": None})
    sys.stdout.buffer.write(serialize(r))
    sys.stdout.buffer.flush()
    return EXITS[r["code"]]


if __name__ == "__main__":
    raise SystemExit(main())

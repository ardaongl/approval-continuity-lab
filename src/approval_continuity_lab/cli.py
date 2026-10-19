"""Explicit process boundary: bounded input, signal flag and descriptor-safe output."""
import fcntl
import os
import signal
import sys
from .models import EXITS, Failure, MAX_INT
from .report import report, serialize, set_error
from .validation import decode, check, invalid

HELP = """Approval Continuity Lab 0.1.0
Usage:
  acl init|propose|decide|execute|revoke|admin-update --db PATH --actor ID --now-ms INT --input PATH [--context ID] [--format json|text]
  acl review --db PATH --actor ID --now-ms INT --proposal-id ID [--context ID] [--format json|text]
  acl inspect --db PATH --actor ID --now-ms INT --kind proposal|approval|execution --id ID [--context ID] [--format json|text]
  acl scenario list [--format json|text]
  acl scenario run D01..D14|all [--format json|text]
Input '-' reads stdin. Personas are trusted lab assertions, not authentication.
Effects cover only one simulated SQLite service. No live deployment or network.
"""
VERSION = b"Approval Continuity Lab 0.1.0\n"


class Cancellation:
    def __init__(self):
        self.cancelled = False

    def handle(self, signum, frame):
        self.cancelled = True

    def is_cancelled(self):
        return self.cancelled


class Clock:
    def __init__(self, now):
        self.now = now

    def now_ms(self):
        return self.now


def stdout_ready():
    try:
        if sys.stdout is None:
            return False
        fd = sys.stdout.fileno()
        os.fstat(fd)
        return fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
    except (OSError, ValueError, AttributeError):
        return False


def diagnostic(code):
    try:
        if sys.stderr is not None:
            os.write(sys.stderr.fileno(), ("acl: " + code + "\n").encode("ascii"))
    except (OSError, ValueError, AttributeError):
        sys.stderr = None
        sys.__stderr__ = None


def emit(encoded, code, cancellation=None):
    try:
        fd = sys.stdout.fileno()
        view = memoryview(encoded)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("No output progress")
            view = view[written:]
        if cancellation is not None and cancellation.is_cancelled():
            code = "INTERRUPTED"
    except (OSError, ValueError, AttributeError):
        # All output uses unbuffered descriptors, and broken streams are removed
        # from interpreter shutdown paths. Never emit a second report.
        sys.stdout = sys.__stdout__ = None
        code = "OUTPUT_IO"
    if code != "OK":
        diagnostic(code)
    return EXITS[code]


def parse(argv):
    verbs = {"init", "propose", "review", "decide", "execute", "revoke", "inspect", "admin-update"}
    if not argv:
        raise Failure("INPUT_INVALID")
    if argv[0] == "scenario":
        if len(argv) >= 2 and argv[1] == "list":
            command, rest, selected = "scenario-list", argv[2:], None
        elif len(argv) >= 3 and argv[1] == "run":
            command, rest, selected = "scenario-run", argv[3:], argv[2]
            if selected not in ("all", *["D%02d" % n for n in range(1, 15)]):
                raise Failure("INPUT_INVALID")
        else:
            raise Failure("INPUT_INVALID")
        allowed, required = {"format"}, set()
    elif argv[0] in verbs:
        command, rest, selected = argv[0], argv[1:], None
        common = {"db", "actor", "now-ms", "context", "format"}
        required = {"db", "actor", "now-ms"}
        specific = {"review": {"proposal-id"}, "inspect": {"kind", "id"}}.get(command, {"input"})
        allowed = common | specific
        required |= specific
    else:
        raise Failure("INPUT_INVALID")
    options = {}
    if len(rest) % 2:
        raise Failure("INPUT_INVALID")
    for i in range(0, len(rest), 2):
        flag, value = rest[i:i+2]
        if not flag.startswith("--") or flag[2:] not in allowed or flag[2:] in options:
            raise Failure("INPUT_INVALID")
        options[flag[2:]] = value
    if required - options.keys() or options.get("format", "json") not in ("json", "text"):
        raise Failure("INPUT_INVALID")
    if "now-ms" in options:
        value = options["now-ms"]
        if not value.isascii() or not value.isdigit() or len(value) > 16 or int(value) > MAX_INT:
            raise Failure("INPUT_INVALID")
        options["now-ms"] = int(value)
        check(options["actor"], "id", "/actor")
        if "context" in options:
            check(options["context"], "id", "/context")
    return command, options, selected


def main(argv=None, *, observer=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not stdout_ready():
        diagnostic("OUTPUT_IO")
        return 74
    if "--help" in argv:
        return emit(HELP.encode("ascii"), "OK")
    if "--version" in argv:
        return emit(VERSION, "OK")
    # Preserve an unambiguously recognized format even for another input error.
    format = "json"
    if argv.count("--format") == 1:
        i = argv.index("--format")
        if i + 1 < len(argv) and argv[i+1] in ("json", "text"):
            format = argv[i+1]
    known = {"init", "propose", "review", "decide", "execute", "revoke", "inspect", "admin-update"}
    command = argv[0] if argv and argv[0] in known else "invalid"
    mode = "SCENARIO" if argv and argv[0] == "scenario" else "REFERENCE"
    if mode == "SCENARIO" and len(argv) > 1 and argv[1] in ("run", "list"):
        command = "scenario-" + argv[1]
    cancellation = Cancellation()
    previous = signal.signal(signal.SIGINT, cancellation.handle)
    try:
        try:
            command, options, selected = parse(argv)
            format = options.get("format", "json")
            if command.startswith("scenario-"):
                from .scenarios import dispatch
                r = dispatch(command, selected)
            else:
                from .mediator import Lab
                if "input" in options:
                    try:
                        if options["input"] == "-":
                            raw = sys.stdin.buffer.read(65537)
                        else:
                            with open(options["input"], "rb") as f:
                                raw = f.read(65537)
                    except (OSError, AttributeError, ValueError):
                        raise Failure("INPUT_IO")
                    body = decode(raw)
                with Lab.open(options["db"], Clock(options["now-ms"]), observer, cancellation) as lab:
                    caller = {"actor_id": options["actor"], "context_id": options.get("context")}
                    if command == "review":
                        r = lab.review(options["proposal-id"], caller)
                    elif command == "inspect":
                        r = lab.inspect(options["kind"], options["id"], caller)
                    else:
                        method = {"init": "initialize", "admin-update": "admin_update"}.get(command, command)
                        r = getattr(lab, method)(body, caller)
        except Failure as exc:
            r = set_error(report(command, mode=mode), exc.code, exc.details)
        except Exception:
            r = set_error(report(command, mode=mode), "INTERNAL_ERROR")
        if cancellation.is_cancelled() and r["code"] != "OUTPUT_IO":
            r.update(code="INTERRUPTED", outcome="interrupted")
        try:
            encoded = serialize(r, format)
        except Exception:
            r = set_error(report(command, mode=mode), "INTERNAL_ERROR")
            encoded = serialize(r, format)
        return emit(encoded, r["code"], cancellation)
    finally:
        signal.signal(signal.SIGINT, previous)

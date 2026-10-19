"""Bounded pipe coordinator for the fixed scenario worker roles."""
import json
import os
import select
import signal
import subprocess
import sys
import time


class Worker:
    def __init__(self, path, role, python=None):
        ready_r, ready_w = os.pipe()
        release_r, release_w = os.pipe()
        self.ready, self.release_fd = ready_r, release_w
        self.events, self.held, self.buffer = [], False, b""
        self.deadline = time.monotonic() + 15
        self.process = None
        try:
            self.process = subprocess.Popen([python or sys.executable, "-I", "-B", "-m", "approval_continuity_lab.scenario_worker", "--db", str(path), "--role", role, "--ready-fd", str(ready_w), "--release-fd", str(release_r)], pass_fds=(ready_w, release_r), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        finally:
            os.close(ready_w)
            os.close(release_r)
            if self.process is None:
                os.close(ready_r)
                os.close(release_w)

    def event(self):
        timeout = min(5, self.deadline - time.monotonic())
        while b"\n" not in self.buffer:
            if timeout <= 0 or not select.select([self.ready], [], [], timeout)[0]:
                raise RuntimeError("Worker rendezvous timed out")
            data = os.read(self.ready, 4096)
            if not data:
                return None
            self.buffer += data
            timeout = min(5, self.deadline - time.monotonic())
        line, self.buffer = self.buffer.split(b"\n", 1)
        point = line.decode("ascii")
        self.events.append(point)
        self.held = True
        return point

    def release(self):
        if self.held:
            os.write(self.release_fd, b"+")
            self.held = False

    def reach(self, target):
        self.release()
        while True:
            point = self.event()
            if point is None:
                raise RuntimeError("Worker exited before " + target)
            if point == target:
                return
            self.release()

    def finish(self):
        self.release()
        while self.event() is not None:
            self.release()
        stdout, stderr = self.process.communicate(timeout=max(0.1, self.deadline-time.monotonic()))
        if stderr:
            raise RuntimeError("Worker produced stderr")
        value = json.loads(stdout)
        self.events.append({"exit": self.process.returncode, "report": value})
        return value

    def kill(self):
        self.process.kill()
        stdout, stderr = self.process.communicate(timeout=5)
        if self.process.returncode != -signal.SIGKILL or stdout or stderr:
            raise RuntimeError("Unexpected crash observation")
        self.events.append({"exit": self.process.returncode})

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.communicate(timeout=5)
        if self.process:
            for stream in (self.process.stdout, self.process.stderr):
                if stream:
                    stream.close()
        for fd in (self.ready, self.release_fd):
            if fd is not None:
                os.close(fd)
        self.ready = self.release_fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

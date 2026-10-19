"""Install a calibrated Python audit guard into the explicit test environment.

This is test orchestration, never runtime product configuration. It blocks
Python socket connect/DNS events, not arbitrary native syscalls or a hostile host.
"""
from pathlib import Path
import sysconfig

GUARD = '''import sys
def _acl_test_network_guard(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr'):
        raise RuntimeError('ACL_OFFLINE_NETWORK_BLOCKED')
sys.addaudithook(_acl_test_network_guard)
'''

if __name__ == "__main__":
    target = Path(sysconfig.get_path("purelib")) / "sitecustomize.py"
    if target.exists() and target.read_text() != GUARD:
        raise SystemExit("Refusing to overwrite another sitecustomize.py")
    target.write_text(GUARD)

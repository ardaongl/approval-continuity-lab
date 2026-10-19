import json
from pathlib import Path
import os
import subprocess
import sys
from tests.support.base import Case
from tests.support.evidence import save


class RuntimeBoundary(Case):
    def test_calibrated_import_help_version_and_invalid_no_application_io(self):
        script=r'''
import sys,os,json
events=[]
def hook(event,args):
 if event=='open':
  path=str(args[0]);mode=args[1];flags=args[2]
  # Import machinery's source/cache/shared library reads are interpreter IO.
  write=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT))
  if not write and path.endswith(('.py','.pyc','.so')):return
  events.append((event,path));raise RuntimeError('blocked application file IO')
 if event in ('sqlite3.connect','tempfile.mkdtemp','tempfile.mkstemp','subprocess.Popen','socket.connect'):
  events.append((event,'blocked'));raise RuntimeError('blocked application IO')
sys.addaudithook(hook)
for mode in ('r','w'):
 try:open('calibration-control',mode)
 except RuntimeError:pass
 else:raise AssertionError('audit hook failed calibration')
assert len(events)==2;events.clear()
import approval_continuity_lab
assert not events,events
from approval_continuity_lab import Lab
from approval_continuity_lab.cli import main,Clock
Lab.open('never-create.sqlite',Clock(1))
mode=sys.argv[1]
argv={'help':['--help','--db','never-create.sqlite','--input','never-read.json'], 'version':['--version'], 'invalid':['execute','--db','never-create.sqlite','--input','never-read.json']}[mode]
code=main(argv)
assert code==(2 if mode=='invalid' else 0),code
assert not events,events
'''
        inventory=sorted(str(x.relative_to(self.path.parent)) for x in self.path.parent.rglob('*'))
        for mode in ('help','version','invalid'):
            p=subprocess.run([sys.executable,'-I','-B','-c',script,mode],cwd=self.path.parent,capture_output=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertNotIn(b'Traceback',p.stderr)
            self.assertEqual(sorted(str(x.relative_to(self.path.parent)) for x in self.path.parent.rglob('*')),inventory)
        save('runtime-boundary',{'launch':[sys.executable,'-I','-B','-c','<audit harness>'],'calibrated_read_write_guard':True,'before':inventory,'after':inventory,'blind_spots':['Python audit hooks do not intercept every native/OS operation','Import source/cache/shared-library reads excluded','No universal OS-write prevention claim']})

    def test_console_and_module_help_version_do_not_create_files(self):
        for base in ([str(Path(sys.executable).parent/'acl')],[sys.executable,'-I','-B','-m','approval_continuity_lab']):
            for args,expected in [(['--help'],0),(['--version'],0),(['unknown'],2)]:
                p=subprocess.run(base+args,cwd=self.path.parent,capture_output=True,timeout=15)
                self.assertEqual(p.returncode,expected,p.stderr);self.assertEqual(list(self.path.parent.iterdir()),[])

import errno
import json
import os
from pathlib import Path
import select
import signal
import sqlite3
import subprocess
import sys
from tests.support.base import Case, asset, rows, snapshot, FIXTURES
from tests.support.evidence import save


class FaultMatrix(Case):
    def commands(self):
        return [[str(Path(sys.executable).parent/'acl')],[sys.executable,'-I','-B','-m','approval_continuity_lab']]

    def child(self,base,args,closed=(),**kwargs):
        def close():
            for fd in closed:
                try:os.close(fd)
                except OSError:pass
        return subprocess.run(base+args,preexec_fn=close if closed else None,capture_output=True,timeout=15,**kwargs)

    def test_success_domain_input_and_real_descriptor_closure(self):
        self.seed();initial=snapshot(self.path)
        execute=['execute','--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600','--input',str(FIXTURES/'execution-input.json')]
        for base in self.commands():
            for closed in [(1,),(1,2)]:
                for args in [execute,['nonsense'],['--help']]:
                    p=self.child(base,args,closed);self.assertEqual(p.returncode,74);self.assertEqual(p.stdout,b'');self.assertNotIn(b'Traceback',p.stderr)
                    self.assertEqual(snapshot(self.path),initial)
            for closed in [(),(2,)]:
                for args,expected in [(['--version'],0),(['unknown'],2),(['review','--db',str(self.path),'--actor','req_b','--context','c2','--now-ms','1600','--proposal-id','p1'],3)]:
                    p=self.child(base,args,closed);self.assertEqual(p.returncode,expected,p.stderr);self.assertNotIn(b'Traceback',p.stderr)
                    if expected==0:self.assertEqual(p.stdout,b'Approval Continuity Lab 0.1.0\n')
                    else:self.assertEqual(json.loads(p.stdout)['code'],'INPUT_INVALID' if expected==2 else 'CALLER_MISMATCH')
                    if closed:self.assertEqual(p.stderr,b'')
                    else:self.assertEqual(p.stderr,b'' if expected==0 else b'acl: '+json.loads(p.stdout)['code'].encode()+b'\n')
        # Prove the closure fixture reaches real CPython None streams.
        for fd in (1,2):
            other=2 if fd==1 else 1
            code=f'import os,sys;os.write({other},str(sys.stdout is None if {fd}==1 else sys.stderr is None).encode())'
            p=self.child([sys.executable,'-I','-B','-c',code],[],(fd,))
            self.assertEqual(p.stderr if other==2 else p.stdout,b'True')

    def test_actual_epipe_small_large_and_other_output_error(self):
        records=[]
        for size in (16,262144):
            read,write=os.pipe();ready_r,ready_w=os.pipe();release_r,release_w=os.pipe()
            code='''import os,sys
from approval_continuity_lab.cli import stdout_ready,emit
ready,release,n=map(int,sys.argv[1:]);assert stdout_ready()
os.write(ready,b"ready");assert os.read(release,1)==b"+"
raise SystemExit(emit(b"x"*n,"OK"))
'''
            try:
                p=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(ready_w),str(release_r),str(size)],stdout=write,stderr=subprocess.PIPE,pass_fds=(ready_w,release_r))
                os.close(ready_w);os.close(release_r);os.close(write)
                self.assertTrue(select.select([ready_r],[],[],5)[0]);self.assertEqual(os.read(ready_r,5),b'ready')
                os.close(read);os.write(release_w,b'+')
                _,stderr=p.communicate(timeout=15);self.assertEqual(p.returncode,74);self.assertEqual(stderr,b'acl: OUTPUT_IO\n')
                records.append({'size':size,'exit':p.returncode,'stderr':stderr.decode()})
            finally:
                if p.poll() is None:p.kill();p.communicate(timeout=5)
                for fd in (ready_r,release_w):os.close(fd)
        # Independent kernel calibration: open write end, zero readers -> EPIPE.
        read,write=os.pipe();os.close(read)
        try:
            with self.assertRaises(OSError) as e:os.write(write,b'x')
            self.assertEqual(e.exception.errno,errno.EPIPE)
        finally:os.close(write)
        # A directory is an open, valid descriptor that cannot accept bytes.
        p=subprocess.run([sys.executable,'-I','-B','-c','import os,sys;from approval_continuity_lab.cli import emit;f=os.open(".",os.O_RDONLY);os.dup2(f,1);raise SystemExit(emit(b"x","OK"))'],capture_output=True,timeout=15)
        self.assertEqual(p.returncode,74);self.assertEqual(p.stderr,b'acl: OUTPUT_IO\n')
        save('process-epipe',{'kernel_errno':errno.EPIPE,'cases':records})

    def test_epipe_after_actual_commit_does_not_repeat_effect(self):
        self.seed()
        read,write=os.pipe();os.close(read)
        args=self.commands()[1]+['execute','--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600','--input',str(FIXTURES/'execution-input.json')]
        try:p=subprocess.run(args,stdout=write,stderr=subprocess.PIPE,timeout=15)
        finally:os.close(write)
        self.assertEqual(p.returncode,74);self.assertEqual(p.stderr,b'acl: OUTPUT_IO\n')
        self.assertEqual(rows(self.path,'services')[0]['revision'],2);self.assertTrue(self.execute()['replayed'])

    def test_sigint_barriers_at_precommit_and_postcommit(self):
        from approval_continuity_lab import Lab
        for i,point in enumerate(('before_commit','after_commit_before_response')):
            self.path=self.path.with_name(f'signal{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            ready_r,ready_w=os.pipe();release_r,release_w=os.pipe()
            code='''import os,select,sys
from approval_continuity_lab.cli import main
point,ready,release=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
class Observer:
 def reached(self,p):
  if p==point:
   os.write(ready,b"ready");assert select.select([release],[],[],5)[0];assert os.read(release,1)==b"+"
raise SystemExit(main(sys.argv[4:],observer=Observer()))
'''
            args=['execute','--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600','--input',str(FIXTURES/'execution-input.json')]
            p=subprocess.Popen([sys.executable,'-I','-B','-c',code,point,str(ready_w),str(release_r),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,pass_fds=(ready_w,release_r))
            os.close(ready_w);os.close(release_r)
            try:
                self.assertTrue(select.select([ready_r],[],[],5)[0]);self.assertEqual(os.read(ready_r,5),b'ready')
                held=snapshot(self.path);os.kill(p.pid,signal.SIGINT);os.write(release_w,b'+')
                stdout,stderr=p.communicate(timeout=15)
                self.assertEqual(p.returncode,130,stderr);self.assertEqual(stderr,b'acl: INTERRUPTED\n')
                r=json.loads(stdout);self.assertEqual(r['effect_status'],'none' if i==0 else 'committed')
                final=snapshot(self.path);self.assertEqual(len(final['executions']),i)
                self.assertEqual(final['services'][0]['revision'],1+i)
                save(f'process-sigint-{i}',{'held_sql':held,'final_sql':final,'exit':p.returncode,'stdout':r,'stderr':stderr.decode()})
            finally:
                if p.poll() is None:p.kill();p.communicate(timeout=5)
                os.close(ready_r);os.close(release_w)

    def test_cli_validation_and_input_io(self):
        self.seed();before=snapshot(self.path);base=self.commands()[1]
        common=['--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600']
        for args,code in [(['execute',*common,'--input','/missing/input'],'INPUT_IO'),(['execute',*common,'--input','-','--now-ms','1'],'INPUT_INVALID'),(['execute',*common,'--input','-','--format','text'],'INPUT_INVALID')]:
            p=self.child(base,args,input=b'not json');self.assertEqual(p.returncode,66 if code=='INPUT_IO' else 2);self.assertEqual(p.stderr,b'acl: '+code.encode()+b'\n')
        self.assertEqual(snapshot(self.path),before)

    def test_closed_stderr_preserves_real_mutation_and_golden(self):
        from approval_continuity_lab import Lab
        for i,base in enumerate(self.commands()):
            self.path=self.path.with_name(f'closed-error-{i}.sqlite');self.lab=Lab.open(self.path,self.clock);self.seed()
            args=['execute','--db',str(self.path),'--actor','req_a','--context','c1','--now-ms','1600','--input',str(FIXTURES/'execution-input.json')]
            p=self.child(base,args,(2,));self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,b'');self.assertEqual(p.stdout,(FIXTURES/'d01-report.golden.json').read_bytes())
            self.assertEqual(rows(self.path,'services')[0]['revision'],2);self.assertEqual(len(rows(self.path,'executions')),1)

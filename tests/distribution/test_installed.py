"""Clean build/archive/offline install gates; no source checkout import fallback."""
import email
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
import zipfile
from tests.support.base import ROOT, FIXTURES
from tests.support.evidence import save

NETWORK_GUARD = '''import sys
def _acl_network_guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr'):
  raise RuntimeError('ACL_OFFLINE_NETWORK_BLOCKED')
sys.addaudithook(_acl_network_guard)
'''


class InstalledDistribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='acl-distribution-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory=Path(cls.temp.name)
        cls.transcript=[]
        cls.wheelhouse=Path(os.environ.get('ACL_WHEELHOUSE',str(ROOT/'.local-verification/build/wheelhouse'))).resolve()
        if not cls.wheelhouse.is_dir():raise RuntimeError('Prepare pinned wheelhouse before running distribution gates')
        cls.source=cls.directory/'source'
        shutil.copytree(ROOT,cls.source,ignore=shutil.ignore_patterns('.git','.venv','.local-verification','build','dist','__pycache__','*.egg-info'))
        cls.builder=cls.create_env('builder',tools=True)
        cls.artifacts=cls.directory/'artifacts';cls.artifacts.mkdir()
        cls.run_command([str(cls.builder/'bin/python'),'-B','-m','pip','wheel','--no-deps','--no-build-isolation','--wheel-dir',str(cls.artifacts),'.'],cwd=cls.source)
        cls.run_command([str(cls.builder/'bin/python'),'-B','-c','from setuptools.build_meta import build_sdist;import sys;build_sdist(sys.argv[1])',str(cls.artifacts)],cwd=cls.source)
        cls.wheel=next(cls.artifacts.glob('*.whl'));cls.sdist=next(cls.artifacts.glob('*.tar.gz'))
        cls.expanded=cls.directory/'sdist';cls.expanded.mkdir()
        with tarfile.open(cls.sdist) as archive:archive.extractall(cls.expanded,filter='data')
        cls.sdist_source=next(cls.expanded.iterdir())
        cls.rebuilt_dir=cls.directory/'rebuilt';cls.rebuilt_dir.mkdir()
        cls.run_command([str(cls.builder/'bin/python'),'-B','-m','pip','wheel','--no-deps','--no-build-isolation','--wheel-dir',str(cls.rebuilt_dir),'.'],cwd=cls.sdist_source)
        cls.rebuilt=next(cls.rebuilt_dir.glob('*.whl'))
        cls.environments=[]
        for name,wheel in [('wheel',cls.wheel),('sdist-wheel',cls.rebuilt)]:
            environment=cls.create_env(name)
            cls.run_command([str(environment/'bin/python'),'-B','-m','pip','install','--no-index','--no-deps',str(wheel)],cwd=cls.directory)
            cls.environments.append(environment)

    @classmethod
    def run_command(cls,argv,cwd=None,expected=0,**kwargs):
        env=dict(os.environ,PIP_NO_INDEX='1',PIP_DISABLE_PIP_VERSION_CHECK='1',PYTHONDONTWRITEBYTECODE='1',PIP_CACHE_DIR=str(cls.directory/'empty-cache'))
        env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
        p=subprocess.run(argv,cwd=cwd or cls.directory,env=env,capture_output=True,timeout=60,**kwargs)
        cls.transcript.append({'argv':argv,'cwd':str(cwd or cls.directory),'exit':p.returncode,'stdout':p.stdout.decode('utf-8','backslashreplace'),'stderr':p.stderr.decode('utf-8','backslashreplace')})
        if p.returncode!=expected:raise AssertionError(cls.transcript[-1])
        return p

    @classmethod
    def create_env(cls,name,tools=False):
        environment=cls.directory/name
        venv.EnvBuilder(with_pip=True).create(environment)
        site=environment/'lib'/('python%d.%d'%sys.version_info[:2])/'site-packages'
        (site/'sitecustomize.py').write_text(NETWORK_GUARD)
        if tools:
            cls.run_command([str(environment/'bin/python'),'-B','-m','pip','install','--no-index','--no-deps','--require-hashes','--find-links',str(cls.wheelhouse),'-r',str(ROOT/'requirements-build.lock')])
            cls.run_command([str(environment/'bin/python'),'-I','-B','-m','pip','check'])
        return environment

    def test_archive_inventory_metadata_assets_and_links(self):
        with zipfile.ZipFile(self.wheel) as z:
            names=set(z.namelist());metadata=email.message_from_bytes(z.read(next(n for n in names if n.endswith('.dist-info/METADATA'))))
            self.assertEqual(metadata['Name'],'approval-continuity-lab');self.assertEqual(metadata['Version'],'0.1.0');self.assertEqual(metadata['Requires-Python'],'==3.12.*')
            self.assertIsNone(metadata.get('Requires-Dist'));self.assertEqual(metadata['License-Expression'],'MIT')
            self.assertFalse(re.search(r'\]\((?![a-zA-Z]+:)[^)]+\)',metadata.get_payload()))
            self.assertTrue(any(n.endswith('/LICENSE') for n in names))
            for fixture in FIXTURES.iterdir():
                member='approval_continuity_lab/documentation/docs/fixtures/'+fixture.name
                self.assertEqual(z.read(member),fixture.read_bytes())
            for path in list((ROOT/'docs').glob('*.md'))+list((ROOT/'docs/contracts').glob('*.md')):
                member='approval_continuity_lab/documentation/'+str(path.relative_to(ROOT));self.assertIn(member,names)
            self.assertFalse(any('/tests/' in n or '__pycache__' in n or '.sqlite' in n or '.local-verification' in n for n in names))
            self.assertIn('approval_continuity_lab/scenarios.py',names);self.assertIn('approval_continuity_lab/scenario_worker.py',names)
        with tarfile.open(self.sdist) as t:
            members=t.getnames();self.assertTrue(any('/tests/acceptance/test_d01.py' in n for n in members))
            for f in FIXTURES.iterdir():self.assertTrue(any(n.endswith('/docs/fixtures/'+f.name) for n in members))
        # Test-owned relative link existence AND heading anchors at actual archive roots.
        for archive in (self.wheel,self.rebuilt,self.sdist):
            if archive.suffix=='.whl':
                with zipfile.ZipFile(archive) as z:content={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
            else:
                with tarfile.open(archive) as t:content={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
            from posixpath import normpath,dirname
            for name,raw in content.items():
                if not name.endswith('.md'):continue
                for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',raw.decode()):
                    target=target.strip('<>')
                    if re.match(r'[a-zA-Z][\w+.-]*:',target):continue
                    relative,sep,anchor=target.partition('#')
                    dest=normpath(dirname(name)+'/'+relative) if relative else name
                    self.assertTrue(dest in content or any(n.startswith(dest.rstrip('/')+'/') for n in content),(archive.name,name,target))
                    if anchor:
                        heads=re.findall(r'^#+ (.*)$',content[dest].decode(),re.M)
                        self.assertIn(anchor,[re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-') for h in heads])
        save('distribution-inventory',{'wheel':sorted(names),'sdist':members,'artifacts':{label:hashlib.sha256(p.read_bytes()).hexdigest() for label,p in [('wheel',self.wheel),('sdist',self.sdist),('rebuilt-wheel',self.rebuilt)]}})

    def test_installed_offline_scenarios_module_console_and_faults(self):
        for environment in self.environments:
            python=str(environment/'bin/python');console=str(environment/'bin/acl')
            p=self.run_command([python,'-I','-B','-c','import approval_continuity_lab;print(approval_continuity_lab.__file__)'])
            self.assertTrue(Path(p.stdout.decode().strip()).is_relative_to(environment));self.assertNotIn(str(ROOT).encode(),p.stdout)
            guard=self.run_command([python,'-I','-B','-c',"import socket;socket.create_connection(('127.0.0.1',9))"],expected=1)
            self.assertIn(b'ACL_OFFLINE_NETWORK_BLOCKED',guard.stderr)
            for base in ([console],[python,'-I','-B','-m','approval_continuity_lab']):
                self.assertEqual(self.run_command(base+['--version']).stdout,b'Approval Continuity Lab 0.1.0\n')
                self.run_command(base+['--help'])
                p=self.run_command(base+['scenario','run','all','--format','json'])
                value=json.loads(p.stdout);self.assertEqual([s['scenario_id'] for s in value['data']['scenarios']],['D%02d'%i for i in range(1,15)])
                self.assertTrue(all(s['verified'] for s in value['data']['scenarios']))
                self.run_command(base+['scenario','run','D08','--format','text'])
                for closed in [(1,),(2,),(1,2)]:
                    def close():
                        for fd in closed:
                            try:os.close(fd)
                            except OSError:pass
                    result=self.run_command(base+['unknown'],expected=74 if 1 in closed else 2,preexec_fn=close)
                    self.assertNotIn(b'Traceback',result.stderr)
                read,write=os.pipe();os.close(read)
                try:
                    result=subprocess.run(base+['--version'],stdout=write,stderr=subprocess.PIPE,cwd=self.directory,timeout=15)
                    self.assertEqual(result.returncode,74);self.assertEqual(result.stderr,b'acl: OUTPUT_IO\n')
                finally:os.close(write)
            # Resource access works from outside the checkout under isolated Python.
            p=self.run_command([python,'-I','-B','-c','from approval_continuity_lab.resources import bytes_asset;import sys;sys.stdout.buffer.write(bytes_asset("d01-report.golden.json"))'])
            self.assertEqual(p.stdout,(FIXTURES/'d01-report.golden.json').read_bytes())
        save('distribution-commands',self.transcript)

    def test_installed_corrupt_metadata_is_unchanged(self):
        # Exercise both the direct wheel and the wheel rebuilt from sdist.
        def snapshot(path):
            with sqlite3.connect(path) as connection:
                connection.row_factory=sqlite3.Row
                return {table:[dict(row) for row in connection.execute('SELECT * FROM '+table+' ORDER BY 1')]
                        for table in ('meta','actors','contexts','tools','policies','eligibility','services','proposals','decisions','executions','transitions')}
        observations=[]
        for environment in self.environments:
            for field,value in (('observed_time_floor_ms',-1),('schema_version',2)):
                for historical in (False,True):
                    with self.subTest(environment=environment.name,field=field,historical=historical):
                        path=self.directory/(environment.name+'-'+field+'-'+str(historical)+'.sqlite')
                        console=str(environment/'bin/acl')
                        def command(verb,actor,now,fixture,context=False,expected=0):
                            argv=[console,verb,'--db',str(path),'--actor',actor,'--now-ms',str(now),'--input',str(FIXTURES/fixture)]
                            if context:argv+=['--context','c1']
                            return self.run_command(argv,expected=expected)
                        command('init','op',1000,'base-config.json')
                        command('propose','req_a',1000,'submission.json',True)
                        command('decide','rev_a',1500,'decision-input.json')
                        if historical:command('execute','req_a',1600,'execution-input.json',True)
                        with sqlite3.connect(path) as connection:
                            connection.execute('PRAGMA ignore_check_constraints=ON')
                            connection.execute('UPDATE meta SET '+field+'=?',(value,))
                        before=snapshot(path)
                        before_hash=hashlib.sha256(path.read_bytes()).hexdigest()
                        p=command('execute','req_a',1600,'execution-input.json',True,65)
                        report=json.loads(p.stdout)
                        self.assertEqual(report['code'],'STATE_CORRUPT')
                        self.assertEqual(p.stderr,b'acl: STATE_CORRUPT\n')
                        self.assertEqual(report['effect_status'],'none')
                        self.assertIsNone(report['data'])
                        self.assertEqual(snapshot(path),before)
                        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before_hash)
                        observations.append(dict(environment=environment.name,field=field,historical=historical,
                                                 report=report,before=before,after=snapshot(path),sha256=before_hash))
        save('distribution-corrupt-meta',observations)

    @classmethod
    def tearDownClass(cls):
        # Retain final build artifacts and complete logs outside clean test dirs.
        target=ROOT/'dist';target.mkdir(exist_ok=True)
        for source in (cls.wheel,cls.sdist):shutil.copy2(source,target/source.name)
        save('distribution-all-commands',cls.transcript)

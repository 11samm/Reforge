"""Tests of the coding agent's host-enforced capability boundary."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from build_shell import FileBroker, ShellRuntime
from adapter.png import ROOT


class BoundaryTests(unittest.TestCase):
    def test_read_write_and_packet_guards(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as tmp:
            parent=Path(tmp)
            app,packet=parent/'app',parent/'packet'
            app.mkdir(); packet.mkdir()
            (packet/'observation.md').write_text('layout')
            broker=FileBroker(app,packet)
            broker.call('shell_write_file',{'path':'src/main.tsx','text':'test'})
            self.assertEqual(broker.call('shell_read_file',{'path':'src/main.tsx'})[0]['text'],'test')
            self.assertEqual(broker.call('shell_read_file',{'path':'layout-packet/observation.md'})[0]['text'],'layout')
            for path in ('../private.txt','D:/private.txt','src/../../private.txt','src\\main.tsx','evidence/reference.png','adapter/minipaint.py','node_modules/private.txt','package.json:stream','/private.txt'):
                for write in (True,False):
                    with self.subTest(path=path,write=write),self.assertRaises(ValueError): broker.path(path,write)
            with self.assertRaises(ValueError): broker.path('layout-packet/observation.md',True)
            with self.assertRaises(ValueError): broker.call('shell_write_file',{'path':'package.json','text':'x','extra':1})
            with self.assertRaises(ValueError): broker.call('exec_command',{'cmd':'dir'})

    def test_real_junction_and_hardlink_escape_denied(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as tmp:
            parent=Path(tmp)
            app,packet,external=parent/'app',parent/'packet',parent/'external'
            for p in (app,packet,external): p.mkdir()
            sentinel=external/'main.tsx'; sentinel.write_text('outside')
            if os.name=='nt':
                result=subprocess.run(['cmd','/c','mklink','/J',str(app/'src'),str(external)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,'Junction test must run, not skip')
            else: (app/'src').symlink_to(external,target_is_directory=True)
            with self.assertRaises(ValueError): FileBroker(app/'src',packet)
            broker=FileBroker(app,packet)
            for write in (False,True):
                with self.assertRaises(ValueError): broker.path('src/main.tsx',write)
            self.assertEqual(sentinel.read_text(),'outside')
            # Remove only the junction itself before TemporaryDirectory cleanup.
            (app/'src').rmdir() if os.name=='nt' else (app/'src').unlink()
            os.link(sentinel,app/'package.json')
            for write in (False,True):
                with self.assertRaises(ValueError): broker.path('package.json',write)

    def test_runtime_denies_non_file_requests(self):
        runtime=object.__new__(ShellRuntime)
        runtime.requests=[]; runtime.broker=FileBroker(); sent=[]
        runtime.send=sent.append
        for method,params in [('item/commandExecution/requestApproval',{}),('item/tool/call',{'tool':'exec_command','arguments':{'cmd':'dir'}}),('item/tool/call',{'tool':'shell_read_file','arguments':{'path':'../smoke.py'}}),('item/tool/call',{'tool':'browser_evaluate','arguments':{'code':'fetch("file:///private")'}}),('item/tool/call',{'tool':'mcp__browser__evaluate','arguments':{'script':'1'}})]:
            runtime.handle_request({'id':1,'method':method,'params':params})
        self.assertTrue(all(not r['success'] for r in runtime.requests))
        self.assertIn('error',sent[0])
        self.assertTrue(all(not reply['result']['success'] for reply in sent[1:]))

    def test_browser_modes_help_and_default(self):
        from unittest.mock import patch
        import adapter.validate as v
        for flags,expected in [([],False),(['--headed'],False),(['--headless'],True)]:
            with patch('sys.argv',['validate',*flags,'--worker','observe','--artifact-dir',str(ROOT/'evidence')]),patch.object(v,'worker',return_value=0) as worker:
                self.assertEqual(v.main(),0)
                self.assertEqual(worker.call_args.args[0].headless,expected)




class WindowPositionTests(unittest.TestCase):
    def test_position_parse_and_headless_rejection(self):
        import argparse
        from unittest.mock import patch
        import adapter.validate as v
        self.assertEqual(v.window_position('-1600,20'),(-1600,20))
        for value in ('1,2,3','1.5,2','33000,0','a,b'):
            with self.assertRaises(argparse.ArgumentTypeError): v.window_position(value)
        with patch('sys.argv',['validate','--headless','--window-position=1600,0']),self.assertRaises(SystemExit) as result:
            v.main()
        self.assertEqual(result.exception.code,2)
        with patch('sys.argv',['validate','--window-position=1600,0','--worker','observe','--artifact-dir',str(ROOT/'evidence')]),patch.object(v,'worker',return_value=0) as worker:
            v.main()
            self.assertFalse(worker.call_args.args[0].headless)
            self.assertEqual(worker.call_args.args[0].window_position,(1600,0))

    def test_launch_changes_only_position(self):
        from unittest.mock import patch, MagicMock
        from adapter.minipaint import MiniPaintAdapter
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as directory:
            for position in (None,(1600,0)):
                playwright=MagicMock()
                with patch('adapter.minipaint.sync_playwright',return_value=playwright):
                    with MiniPaintAdapter(directory,window_position=position): pass
                launch=playwright.start.return_value.chromium.launch.call_args.kwargs
                expected={'headless':False,'timeout':30000}
                if position: expected['args']=['--window-position=1600,0']
                self.assertEqual(launch,expected)
            with self.assertRaises(ValueError): MiniPaintAdapter(directory,headed=False,window_position=(1600,0))

if __name__=='__main__': unittest.main()

"""Offline isolation/transport tests. Synthetic job metadata is explicitly labeled."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from features import live

class LiveTests(unittest.TestCase):
    def test_job_isolation_terminal_cancel_and_worker_disconnect(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(live,'ROOT',Path(temp)), patch.dict(os.environ,{'REFORGE_LIVE_JOB':'a'*32,'REFORGE_LIVE_ENABLED':'1'}):
            s=live.Session('candidate','ready'); s.value['frame']='YWJj'; s.publish()
            job={'id':'a'*32,'status':'running','stage':'Verify','elapsed_seconds':4}
            self.assertEqual(live.snapshot(job)['sessions']['candidate']['frame'],'YWJj')
            self.assertIsNone(live.snapshot({**job,'id':'b'*32})['sessions']['candidate']['frame'])
            for status in ('cancelled','cancelling','accepted','failed'):
                self.assertIsNone(live.snapshot({**job,'status':status})['sessions']['candidate']['frame'])
            with patch.object(live,'alive',return_value=False):
                self.assertEqual(live.snapshot(job)['sessions']['candidate']['state'],'disconnected')
    def test_final_blackout_disables_frame_writes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(live,'ROOT',Path(temp)), patch.dict(os.environ,{'REFORGE_LIVE_JOB':'a'*32,'REFORGE_LIVE_ENABLED':'1'}):
            live.start('feature-reference',{'value':17,'input_path':'/private/inputs/ramp.png'})
            live.hide(); live.action('secret final value',value=99)
            self.assertFalse(live.enabled())
            job={'id':'a'*32,'status':'running','stage':'Verify','elapsed_seconds':4}
            result=live.snapshot(job)
            self.assertTrue(all(s['state']=='hidden' and s['frame'] is None for s in result['sessions'].values()))
            self.assertNotIn('secret',str(result))
    def test_opt_out_never_writes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(live,'ROOT',Path(temp)), patch.dict(os.environ,{'REFORGE_LIVE_ENABLED':'0'}):
            live.start('candidate',{}); live.action('not published')
            self.assertEqual(list(Path(temp).iterdir()),[])

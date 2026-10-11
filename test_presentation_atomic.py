"""No-model regression for Windows readers colliding with live snapshot writes."""
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from features.presentation import atomic, read


def snapshot_reader(directory, stop, messages):
    samples=0; errors=[]
    while not stop.is_set():
        try:
            row=read(Path(directory),'results.json')
            if row['payload']!='x'*64000:errors.append('partial payload')
            samples+=1
            if samples==1:messages.put('ready')
        except Exception as e:errors.append(str(e))
    messages.put({'samples':samples,'errors':errors})


class AtomicPresentation(unittest.TestCase):
    def test_transient_sharing_conflict_keeps_old_snapshot_then_replaces_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'results.json'; atomic(path,{'sequence':0})
            replace=os.replace; attempts=[]
            def conflict(source,target):
                attempts.append(source)
                self.assertEqual(json.loads(path.read_text()),{'sequence':0})
                if len(attempts)<3: raise PermissionError('Synthetic Windows sharing conflict')
                return replace(source,target)
            with patch('features.presentation.os.replace',side_effect=conflict),patch('features.presentation.time.sleep'):
                atomic(path,{'sequence':1})
            self.assertEqual(len(attempts),3)
            self.assertEqual(json.loads(path.read_text()),{'sequence':1})
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_permanent_conflict_is_bounded_and_preserves_both_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'results.json'; atomic(path,{'sequence':0})
            with patch('features.presentation.os.replace',side_effect=PermissionError('Synthetic permanent denial')) as replace,patch('features.presentation.time.sleep'):
                with self.assertRaises(PermissionError): atomic(path,{'sequence':1})
            self.assertEqual(replace.call_count,6)
            self.assertEqual(json.loads(path.read_text()),{'sequence':0})
            evidence=list(Path(tmp).glob('*.tmp'))
            self.assertEqual(len(evidence),1)
            self.assertEqual(json.loads(evidence[0].read_text()),{'sequence':1})

    def test_real_concurrent_readers_never_see_partial_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'results.json'; atomic(path,{'sequence':0,'payload':'x'*64000})
            stop=threading.Event(); errors=[]; samples=[]
            def reader():
                while not stop.is_set():
                    try:
                        row=read(Path(tmp),'results.json'); samples.append(row['sequence'])
                        if row['payload']!='x'*64000: errors.append('partial payload')
                    except Exception as e: errors.append(str(e))
            workers=[threading.Thread(target=reader) for _ in range(4)]
            for worker in workers:worker.start()
            try:
                for sequence in range(1,101):atomic(path,{'sequence':sequence,'payload':'x'*64000})
            finally:
                stop.set()
                for worker in workers:worker.join()
            self.assertTrue(samples)
            self.assertEqual(errors,[])
            self.assertEqual(json.loads(path.read_text())['sequence'],100)

    def test_service_and_publisher_in_separate_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'results.json'; atomic(path,{'sequence':0,'payload':'x'*64000})
            ctx=multiprocessing.get_context('spawn'); stop=ctx.Event(); messages=ctx.Queue()
            process=ctx.Process(target=snapshot_reader,args=(tmp,stop,messages)); process.start()
            try:
                self.assertEqual(messages.get(timeout=20),'ready')
                for sequence in range(1,101):atomic(path,{'sequence':sequence,'payload':'x'*64000})
            finally:
                stop.set(); process.join(timeout=10)
                if process.is_alive():process.terminate();process.join()
            self.assertEqual(process.exitcode,0)
            result=messages.get(timeout=5)
            self.assertGreater(result['samples'],0)
            self.assertEqual(result['errors'],[])


if __name__=='__main__':unittest.main()

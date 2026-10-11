"""Permanent presentation failures must not erase evidence or authorize acceptance."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from features.learning import AdjustmentHarness
from features import presentation
from features.child import event_emitter
from learning.core import Budget, DEFAULTS, save, digest
from verify_shell import unique_shell_label, DuplicateShellLabelError

class PresentationIsolation(unittest.TestCase):
    def harness(self, root):
        h=object.__new__(AdjustmentHarness)
        h.directory=root/'archive'; h.directory.mkdir()
        h.presentation_directory=root/('feature-'+'a'*32); h.presentation_directory.mkdir()
        h.events=[]; h.budget=Budget(DEFAULTS); h.notify=Mock()
        return h

    def test_permanent_results_denial_continues_experiments_and_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=self.harness(Path(tmp))
            h.emit('checkpoint',state='initial')
            old=(h.presentation_directory/'presentation/results.json').read_bytes()
            timestamp=presentation.results(h.presentation_directory,'a'*32)['snapshot_at']
            original=__import__('os').replace
            def deny(source,target):
                if Path(target).name=='results.json': raise PermissionError('Permanent Windows denial')
                return original(source,target)
            with patch('features.presentation.os.replace',side_effect=deny), patch('features.presentation.time.sleep'):
                save(h.directory/'experiments/probe/preregistered.json',{'input':{'kind':'patches'}})
                save(h.directory/'evidence/probe.json',{'id':'probe','expected_sha256':'original-evidence'})
                proof=digest(h.directory/'evidence/probe.json')
                h.emit('evidence',id='probe',status='OBSERVED')
                evaluation={'build_valid':True,'independent':True,'ui_valid':True,'baseline_pass':True,'cases':[]}
                save(h.directory/'evaluations/candidate-1/evaluation.json',evaluation)
                h.emit('evaluation',label='candidate-1',result=evaluation)
            self.assertEqual(digest(h.directory/'evidence/probe.json'),proof)
            self.assertEqual(json.loads((h.directory/'evaluations/candidate-1/evaluation.json').read_text()),evaluation)
            events=[json.loads(x) for x in (h.directory/'events.jsonl').read_text().splitlines()]
            self.assertEqual([x['event'] for x in events],['checkpoint','evidence','evaluation'])
            self.assertEqual(h.notify.call_count,3)
            self.assertEqual((h.presentation_directory/'presentation/results.json').read_bytes(),old)
            result=presentation.results(h.presentation_directory,'a'*32)
            self.assertEqual(result['presentation']['state'],'degraded')
            self.assertEqual(result['snapshot_at'],timestamp)
            self.assertEqual(result['experiments'],[])
            self.assertEqual(result['candidates'],[])
            self.assertEqual(len((h.directory/'presentation-failures.jsonl').read_text().splitlines()),2)
            self.assertEqual(len(list((h.presentation_directory/'presentation').glob('*.tmp'))),2)
            h.emit('stop',status='unresolved')
            self.assertEqual(presentation.results(h.presentation_directory,'a'*32)['presentation']['state'],'available')
            self.assertEqual(len((h.directory/'presentation-failures.jsonl').read_text().splitlines()),2)

    def test_harness_run_reaches_candidate_decision_after_permanent_failure(self):
        # Controlled workers and builder: exercises the real sequential run loop,
        # experiment persistence, frozen suite and candidate decisions with no model.
        with tempfile.TemporaryDirectory() as tmp:
            h=self.harness(Path(tmp)); h.app=Path(tmp)/'app'; (h.app/'src').mkdir(parents=True)
            (h.app/'src/main.tsx').write_text('// target absent')
            h.op={'source':'src/brightness.ts'}; h.operation='brightness'; h.config={**DEFAULTS,'fresh_experiments':2,'candidates':1}
            h.domain={'min':-100,'max':100,'step':1,'default':0}; h.spec={}
            h.evidence=[]; h.attempts=[]; h.first_acceptance=None; h.best=Path(tmp)/'checkpoint'
            h.checkpoints=Mock(); h.checkpoints.snapshot.return_value=h.best
            h.baseline=Mock(return_value=True); h.guard=Mock(); h.build_contract=Mock(); h.builder=Mock()
            plans=[{'question':'Synthetic bounded probe','hypotheses':['A','B'],
                    'input':{'kind':'patches','width':3,'height':3},'value':v,
                    'predictions':['A','B'],'usefulness':'Synthetic worker only'} for v in (-50,50)]
            h.ask=Mock(return_value={'plans':plans})
            def worker(kind,request,directory,timeout):
                if kind=='feature-reference':
                    return {'status':'observed','accepted':request['value'],'output_path':request['input_path']}
                return {'status':'passed'}
            h.worker=worker
            h.evaluate=Mock(return_value={'build_valid':False,'independent':True,'ui_valid':True,'baseline_pass':True,'cases':[]})
            def cleanup():
                save(h.directory/'report.json',{'status':'unresolved','attempts':h.attempts,'stop':h.stop})
            h.cleanup=cleanup
            with patch('features.presentation.publish',side_effect=PermissionError('Permanent display failure')):
                h.run()
            h.builder.assert_called_once(); h.evaluate.assert_called_once_with('candidate-1')
            self.assertEqual(h.attempts[0]['status'],'rejected')
            self.assertEqual(len(list((h.directory/'evidence').glob('*.json'))),2)
            self.assertTrue((h.directory/'suite.json').is_file())
            self.assertTrue((h.directory/'report.json').is_file())
            self.assertEqual(h.stop,'candidate_budget_exhausted')

    def test_permanent_copy_failure_is_diagnostic_not_fake_missing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=self.harness(Path(tmp)); h.emit('checkpoint')
            # A publisher filesystem error, including mkdir/copy, is contained.
            with patch('features.presentation.publish',side_effect=OSError('Permanent filesystem failure')):
                h.emit('evidence',id='original')
            self.assertEqual(presentation.results(h.presentation_directory,'a'*32)['presentation']['failure']['message'],'Permanent filesystem failure')
            h.notify.assert_called_with('evidence',id='original')

    def test_integrity_and_authoritative_write_failure_still_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            h=self.harness(Path(tmp))
            with patch('features.presentation.publish',side_effect=ValueError('Integrity failure')):
                with self.assertRaisesRegex(ValueError,'Integrity'):h.emit('evaluation')
            with patch('learning.run.Path.open',side_effect=PermissionError('Authoritative evidence denied')):
                with self.assertRaisesRegex(PermissionError,'Authoritative'):h.emit('evidence')

    def test_broken_transport_commits_pipeline_evidence_and_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); transport=Mock(side_effect=BrokenPipeError('Disconnected reader'))
            emit=event_emitter(root,transport)
            emit('stage',stage='Investigate'); emit('usage',usage={'total_tokens':17})
            rows=[json.loads(x) for x in (root/'pipeline-events.jsonl').read_text().splitlines()]
            self.assertEqual(rows[1]['data']['usage']['total_tokens'],17)
            self.assertEqual(len((root/'transport-failures.jsonl').read_text().splitlines()),2)

    def test_live_filesystem_failure_preserves_last_frame_and_records_diagnostics(self):
        import os
        from features import live
        with tempfile.TemporaryDirectory() as tmp, patch.object(live,'ROOT',Path(tmp)), patch.dict(os.environ,{'REFORGE_LIVE_JOB':'a'*32,'REFORGE_LIVE_ENABLED':'1'}):
            session=live.Session('candidate','ready')
            session.value.update(frame='YWJj',captured_at=123,frame_sequence=1)
            session.publish()
            old=(Path(tmp)/'.scratch/live'/('a'*32)/'candidate.json').read_bytes()
            with patch.object(live,'write',side_effect=PermissionError('Permanent stream denial')):
                session.action('Next action')
            self.assertEqual((Path(tmp)/'.scratch/live'/('a'*32)/'candidate.json').read_bytes(),old)
            job={'id':'a'*32,'status':'running','stage':'Verify','elapsed_seconds':1}
            saved=live.snapshot(job)['sessions']['candidate']
            self.assertEqual(saved['captured_at'],123)
            self.assertEqual(saved['presentation']['state'],'degraded')
            self.assertIn('Permanent stream denial',saved['presentation']['failure']['message'])

    def test_duplicate_label_feedback_includes_hidden_nodes_and_correction(self):
        page=Mock(); page.get_by_text.return_value.count.return_value=2
        with self.assertRaises(DuplicateShellLabelError) as caught:unique_shell_label(page,'No image loaded')
        self.assertEqual(caught.exception.diagnostic['label'],'No image loaded')
        self.assertEqual(caught.exception.diagnostic['count'],2)
        self.assertIn('distinct text',caught.exception.diagnostic['required_correction'])
        page.get_by_text.assert_called_once_with('No image loaded',exact=True)

if __name__=='__main__':unittest.main()

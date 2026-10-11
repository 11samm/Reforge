"""Explicitly synthetic offline presentation fixtures; no model or browser calls."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import Image
from learning.core import save, digest
from features import presentation
from features.demos import Demos, validate
from features.jobs import JobStore
from features.service import server


class PresentationTests(unittest.TestCase):
    def test_real_record_fields_missing_artifacts_and_scoped_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); archive=root/'archive'; job=root/('feature-'+'a'*32)
            job.mkdir(); archive.mkdir()
            save(archive/'experiments/adjustment-1/preregistered.json',{'question':'Synthetic fixture','input':{'kind':'patches'},'value':3})
            path=archive/'inputs/adjustment-1.png'; path.parent.mkdir(); Image.new('RGBA',(2,2),(1,2,3,4)).save(path)
            save(archive/'evaluations/candidate-1/evaluation.json',{'build_valid':True,'ui_valid':False,'independent':True,'error':{'message':'Recorded accessible label failure'},'cases':[{'case_id':'adjustment-1','status':'failed','reasons':['Recorded missing output'],'metrics':None}]})
            presentation.publish(job,archive,[{'event':'rejection','reason':'UI failed'}])
            result=presentation.results(job,'a'*32)
            self.assertEqual(result['experiments'][0]['plan']['input']['kind'],'patches')
            self.assertEqual(result['experiments'][0]['artifacts'][1]['status'],'missing')
            self.assertEqual(result['candidates'][0]['result']['error']['message'],'Recorded accessible label failure')
            self.assertIsNone(result['candidates'][0]['cases'][0]['metrics'])
            item=result['experiments'][0]['artifacts'][0]
            self.assertTrue(presentation.asset(job,'a'*32,item['id']).is_file())
            other=root/('feature-'+'b'*32); other.mkdir(); presentation.publish(other,archive)
            other_item=presentation.results(other,'b'*32)['experiments'][0]['artifacts'][0]
            self.assertNotEqual(item['id'],other_item['id'])
            with self.assertRaises(ValueError): presentation.asset(job,'a'*32,other_item['id'])
            with self.assertRaises(ValueError): presentation.asset(job,'b'*32,item['id'])
            with self.assertRaises(ValueError): presentation.asset(job,'a'*32,'../../secret')
            with self.assertRaises(ValueError): presentation.asset(job,'a'*32,'0'*64+'.png')
            target=job/'presentation/assets'/item['id']; target.write_bytes(b'changed')
            with self.assertRaises(ValueError): presentation.asset(job,'a'*32,item['id'])
    def test_links_traversal_and_cross_archive_reference_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('../secret','/secret','x\\y','x:y','x/../secret','./secret'):
                with self.assertRaises(ValueError): presentation.safe_file(root,name)
            target=root/'secret'; target.write_text('secret')
            import os
            os.link(target,root/'hardlink')
            with self.assertRaises(ValueError): presentation.safe_file(root,'hardlink')
            archive=root/'archive'; archive.mkdir(); job=root/('feature-'+'a'*32); job.mkdir()
            save(archive/'experiments/x/preregistered.json',{'input':{}})
            save(archive/'evidence/x.json',{'expected':str(target)})
            presentation.publish(job,archive)
            self.assertEqual(presentation.results(job,'a'*32)['experiments'][0]['artifacts'][1]['status'],'missing')
    def test_immutable_preview_and_job_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); app=root/'app'; (app/'dist/assets').mkdir(parents=True)
            (app/'dist/index.html').write_text('<script src="/assets/a.js"></script>')
            (app/'dist/assets/a.js').write_text('// synthetic fixture')
            (app/'dist/secret.txt').write_text('not served')
            output=root/'job'; output.mkdir(); Demos.snapshot(output,app,'a'*32)
            self.assertIn('./assets/',Demos.preview_file(output,'a'*32,'index.html').read_text())
            for ident,name in [('b'*32,'index.html'),('a'*32,'secret.txt'),('a'*32,'../secret.txt')]:
                with self.assertRaises(ValueError): Demos.preview_file(output,ident,name)
            (app/'dist/assets/a.js').write_text('// changed source dist')
            self.assertEqual(Demos.preview_file(output,'a'*32,'assets/a.js').read_text(),'// synthetic fixture')
    def test_prepared_binding_and_changed_editor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch('features.demos.ROOT',Path(tmp)):
            root=Path(tmp); ident='a'*32; app=root/'dev-workspaces'/('feature-'+ident); (app/'src').mkdir(parents=True)
            path=app/'src/main.tsx'; path.write_text('// synthetic absent editor')
            record={'feature':'brightness','app':str(app),'target_absent':True,'model_invoked':False,'files':{'src/main.tsx':digest(path)}}
            prepared={'id':ident,'preparation':record}
            store=JobStore(root/'jobs'); job=store.create('Implement Brightness',prepared)
            self.assertEqual(job['id'],ident); self.assertEqual(job['prepared_demo'],prepared)
            store.cancel(ident); store.finish(ident,{'status':'cancelled'})
            with self.assertRaises(ValueError): store.create('Implement Brightness',prepared)
            with self.assertRaises(ValueError): validate('Implement Contrast',ident,record)
            path.write_text('// edited')
            with self.assertRaisesRegex(ValueError,'changed'): validate('Implement Brightness',ident,record)
    def test_pipeline_starts_selected_editor_without_preparing_another(self):
        with tempfile.TemporaryDirectory() as tmp, patch('features.demos.ROOT',Path(tmp)), patch('features.pipeline.ROOT',Path(tmp)):
            from features.pipeline import run
            root=Path(tmp); ident='a'*32; app=root/'dev-workspaces'/('feature-'+ident); (app/'src').mkdir(parents=True)
            source=app/'src/main.tsx'; source.write_text('// explicitly synthetic starting editor')
            record={'feature':'brightness','app':str(app),'target_absent':True,'model_invoked':False,'files':{'src/main.tsx':digest(source)}}
            with patch('features.preparation.prepare') as prepare, patch('features.sessions.start_pool',side_effect=RuntimeError('Offline fixture stop before discovery')) as start, patch('learning.run.Harness.worker') as worker:
                with self.assertRaisesRegex(RuntimeError,'Offline fixture stop'): run('Implement Brightness',ident,lambda *a,**k:None,prepared={'id':ident,'preparation':record})
                prepare.assert_not_called(); start.assert_called_once_with(app); worker.assert_not_called()
    def test_disabled_learning_still_allows_no_model_preparation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(Demos,'prepare',return_value={'id':'a'*32,'model_invoked':False}) as prepare, patch('features.service.execute') as execute:
            store=JobStore(tmp); service=server(store,0,False); thread=threading.Thread(target=service.serve_forever,daemon=True); thread.start()
            base=f'http://127.0.0.1:{service.server_port}/api/jobs'
            def post(path,body): return urlopen(Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Reforge-Request':'1'}))
            try:
                with post('/prepare',{'request':'Implement Brightness'}) as response: self.assertFalse(json.load(response)['model_invoked'])
                prepare.assert_called_once_with('Implement Brightness'); execute.assert_not_called()
                with self.assertRaises(HTTPError) as error: post('',{'request':'Implement Brightness','prepared_demo_id':'a'*32})
                self.assertEqual(error.exception.code,409); error.exception.close()
                job=store.create('Implement Brightness')
                with urlopen(base+'/'+job['id']+'/results') as response: self.assertEqual(json.load(response)['experiments'],[])
                with self.assertRaises(HTTPError) as error: urlopen(base+'/'+job['id']+'/preview/index.html')
                self.assertEqual(error.exception.code,400); error.exception.close()
            finally: service.shutdown(); service.server_close(); thread.join()
    def test_final_summary_not_read_until_terminal_and_null_origin_read_only(self):
        with tempfile.TemporaryDirectory() as tmp, patch('features.service.ROOT',Path(tmp)):
            root=Path(tmp); store=JobStore(root/'jobs'); job=store.create('Implement Brightness'); ident=job['id']
            save(root/'evidence/learning'/('feature-'+ident)/'final-summary.json',{'status':'unresolved','reason':'Synthetic final summary'})
            service=server(store,0); thread=threading.Thread(target=service.serve_forever,daemon=True); thread.start()
            base=f'http://127.0.0.1:{service.server_port}/api/jobs/{ident}'
            try:
                with urlopen(base+'/results') as response: self.assertNotIn('final',json.load(response))
                with self.assertRaises(HTTPError) as error: urlopen(Request(base+'/results',headers={'Origin':'null'}))
                self.assertEqual(error.exception.code,403); error.exception.close()
                store.cancel(ident); store.finish(ident,{'status':'cancelled'})
                with urlopen(base+'/results') as response: self.assertEqual(json.load(response)['final']['reason'],'Synthetic final summary')
            finally: service.shutdown(); service.server_close(); thread.join()
    def test_final_summary_keeps_legacy_cases_and_specific_ui_failure(self):
        from types import SimpleNamespace
        from test_features import specification
        from features.pipeline import final_check
        import shutil
        for ui_valid in (True,False):
            with self.subTest(ui_valid=ui_valid), tempfile.TemporaryDirectory() as tmp, patch('features.live.hide') as hide:
                directory=Path(tmp); control=SimpleNamespace(report={'final_baseline_pass':True})
                def worker(owner,kind,request,output,timeout,**kwargs):
                    hide.assert_called_once()
                    if kind=='feature-reference':
                        output.mkdir(parents=True); path=output/'output.png'; shutil.copyfile(request['input_path'],path)
                        return {'status':'observed','output_path':str(path)}
                    return {'build_valid':True,'independent':True,'ui_valid':ui_valid,'error':None if ui_valid else {'message':'Synthetic recorded UI/batch mismatch'},'cases':[{'case_id':row['id'],'status':'passed','classification':'match','metrics':{'synthetic_fixture':True},'reasons':[]} for row in request['suite']['cases']]}
                with patch('learning.run.Harness.worker',side_effect=worker):
                    result=final_check(specification(),directory/'app',control,directory,lambda *a,**k:None)
                summary=json.loads((directory/'final-summary.json').read_text())
                self.assertEqual(result['status'],'accepted' if ui_valid else 'unresolved')
                self.assertEqual(len(summary['cases']),2); self.assertFalse(summary['promoted'])
                if not ui_valid: self.assertEqual(summary['evaluation']['error']['message'],'Synthetic recorded UI/batch mismatch')


if __name__=='__main__': unittest.main()

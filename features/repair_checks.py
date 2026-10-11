"""Trusted reference-free reproducers; model never supplies executable test code."""
import json
import subprocess
import sys
from pathlib import Path
from adapter.png import ROOT
from features.repair import install

def reproduce(case):
    if case['kind']=='schema':
        from features.discovery import output_schema, SCHEMA
        original=json.dumps(SCHEMA,sort_keys=True)
        s=output_schema('Implement Contrast'); p=s['properties']
        assert p['request']=={'type':'string','const':'Implement Contrast'}
        assert p['parameter']=={'type':'string','enum':['Contrast','Contrast:']}
        for k in ('dialog','scope','completion','import_procedure','export_procedure'):
            assert p[k]=={'type':'string'}
        assert p['controls']['items']['properties']['label']=={'type':'string'}
        assert json.dumps(SCHEMA,sort_keys=True)==original
        p['request']['const']='changed'
        assert output_schema('Implement Contrast')['properties']['request']['const']=='Implement Contrast'
    elif case['kind']=='row':
        import html
        from playwright.sync_api import sync_playwright
        from features.browser import resolve
        label=html.escape(case['label']); typ=case['type']
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True); page=browser.new_page()
            markup='<table><tr><td>'+label+':</td><td><input type="'+typ+'"></td></tr></table>'
            page.set_content(markup); field=resolve(page,case['strategy']); assert field.is_visible()
            page.set_content(markup+markup)
            try: resolve(page,case['strategy'])
            except ValueError: pass
            else: raise AssertionError('Duplicate control accepted')
            browser.close()
    else: raise ValueError('Unsupported reproducer')

def main():
    request=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    if request['patch']: install(request['patch'])
    reproduce(request['case'])
    if request['regressions']:
        # Tests execute in this interpreter, so they exercise patched functions.
        import unittest
        suite=unittest.defaultTestLoader.loadTestsFromNames(['test_features','test_smoke','test_adapter','test_shell_boundary','test_evaluator','test_learning','test_brightness'])
        if not unittest.TextTestRunner().run(suite).wasSuccessful(): return 1
    return 0
if __name__=='__main__': raise SystemExit(main())

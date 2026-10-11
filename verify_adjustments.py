"""Offline integration revalidation of frozen visible adjustment cases; no models."""
import argparse
import json
import shutil
import uuid
from pathlib import Path
from adapter.png import ROOT
from evaluator.compare import load_policy
from learning.core import digest, save
from learning.worker import candidate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contrast-archive',type=Path,help='Original accepted learning archive containing visible suite.json and provenance.json')
    args=parser.parse_args()
    directory=ROOT/'evidence/learning'/('offline-feature-integration-'+uuid.uuid4().hex)
    directory.mkdir(parents=True)
    suites=[]
    rows=[]
    for name in ('visible','fresh'):
        for row in json.loads((ROOT/'evidence/brightness'/(name+'-suite.json')).read_text())['cases']:
            rows.append({**row,'input':str(ROOT/row['input']),'expected':str(ROOT/row['expected'])})
    suites.append(('brightness',None,{'id':'saved-brightness-integration','cases':rows,'policy':load_policy()}))
    if args.contrast_archive:
        archive=args.contrast_archive.resolve()
        suite=json.loads((archive/'suite.json').read_text())
        spec=json.loads((archive/'provenance.json').read_text())['feature_spec']
        if spec['feature_id']!='contrast' or suite['policy']!=load_policy(): raise ValueError('Wrong feature or changed policy')
        # Only the visible suite is read; never final outputs or final-suite.json.
        suites.append(('contrast',spec,suite))
    reports={}
    for operation,spec,suite in suites:
        folder=directory/operation; folder.mkdir()
        suite=json.loads(json.dumps(suite))
        for row in suite['cases']:
            target=folder/'inputs'/(row['id']+'.png'); target.parent.mkdir(exist_ok=True)
            if digest(row['input'])!=row['input_sha256']: raise ValueError('Input hash changed')
            shutil.copyfile(row['input'],target); row['input']=str(target)
        save(folder/'suite.json',suite)
        request={'operation':operation,'app':str(ROOT/'generated-app'),'suite':suite,'suite_sha256':digest(folder/'suite.json')}
        if spec: request['spec']=spec
        result=candidate(request,folder); save(folder/'result.json',result)
        passed=bool(result['cases']) and result['build_valid'] and result['independent'] and result['ui_valid'] and all(c['status']=='passed' for c in result['cases'])
        reports[operation]={'passed':passed,'cases':len(result['cases']),'error':result.get('error')}
    save(directory/'summary.json',reports)
    print(json.dumps({'results':reports,'artifacts':str(directory)}))
    return 0 if all(r['passed'] for r in reports.values()) else 1

if __name__=='__main__': raise SystemExit(main())

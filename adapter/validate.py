"""Run a fixed six-experiment development batch, with process deadlines."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .minipaint import MiniPaintAdapter, utc_now, write_json
from .png import ROOT, FIXTURES, EVIDENCE, within


def cases():
    rows=[json.loads(line) for line in (FIXTURES / 'manifest.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    if len(rows)!=2 or {r['case_id'] for r in rows}!={'gb010','gb017'}:
        raise ValueError('Validation requires only the two selected development cases')
    return sorted(rows,key=lambda row:row['case_id'],reverse=True)


def worker(args):
    directory=within(args.artifact_dir,EVIDENCE)
    directory.mkdir(parents=True,exist_ok=True)
    try:
        with MiniPaintAdapter(directory,headed=not args.headless,window_position=args.window_position) as adapter:
            if args.worker=='observe':
                identity=adapter.capture_initial_interface()
                write_json(directory / 'report.json',{'status':'passed','target':identity,'actions':adapter.actions})
                return 0
            case=next(c for c in cases() if c['case_id']==args.worker)
            report=adapter.run_experiment(case,repeat=args.repeat,import_route=args.import_route)
            print(json.dumps({'case_id':case['case_id'],'repeat':args.repeat,'status':report['status'],
                'elapsed_seconds':report['elapsed_seconds'],'errors':report['infrastructure_errors']}),flush=True)
            return 0 if report['status']=='passed' else 1
    except Exception as error:
        write_json(directory / 'report.json',{'status':'infrastructure_failure','case_id':args.worker,
            'repeat':args.repeat,'infrastructure_errors':[{'type':type(error).__name__,'message':str(error)[:2000]}]})
        return 1


def run_worker(args, kind, repeat, directory):
    command=[sys.executable,'-m','adapter.validate','--worker',kind,'--repeat',str(repeat),
             '--artifact-dir',str(directory),'--import-route',args.import_route]
    command.append('--headless' if args.headless else '--headed')
    if args.window_position is not None:
        command.append('--window-position=' + ','.join(map(str,args.window_position)))
    directory.mkdir(parents=True)
    with (directory / 'worker.log').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
            start_new_session=os.name!='nt')
        try:
            proc.wait(timeout=args.case_timeout)
        except subprocess.TimeoutExpired:
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],timeout=10,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                import signal
                os.killpg(proc.pid,signal.SIGKILL)
            proc.wait(timeout=5)
            write_json(directory / 'report.json',{'case_id':kind,'repeat':repeat,'status':'infrastructure_failure',
                'infrastructure_errors':[{'type':'ProcessTimeout','message':f'Case exceeded {args.case_timeout}s; controller tree terminated'}]})
    path=directory / 'report.json'
    if not path.exists():
        write_json(path,{'case_id':kind,'repeat':repeat,'status':'infrastructure_failure',
            'infrastructure_errors':[{'type':'WorkerExit','message':f'Controller exited {proc.returncode} without a report'}]})
    return json.loads(path.read_text(encoding='utf-8'))


def window_position(value):
    import re
    if not re.fullmatch(r'-?\d+,-?\d+', value):
        raise argparse.ArgumentTypeError('Use desktop coordinates X,Y, e.g. --window-position=1600,0')
    coordinates=tuple(map(int,value.split(',')))
    if any(not -32768<=v<=32767 for v in coordinates):
        raise argparse.ArgumentTypeError('Window coordinates must be -32768..32767')
    return coordinates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--headless',action='store_true',help='Unverified for reference equivalence: previous exact comparisons failed; diagnostic only')
    mode.add_argument('--headed',action='store_false',dest='headless',help='Use supported headed Chromium (default), also for debugging/presentation')
    parser.set_defaults(headless=False)
    parser.add_argument('--window-position',type=window_position,help='Headed browser desktop origin X,Y; use another monitor/away from workspace. Viewport remains 1440x1000.')
    parser.add_argument('--case-timeout',type=int,default=120)
    parser.add_argument('--import-route',choices=['auto','file_chooser','data_url'],default='auto')
    parser.add_argument('--worker',choices=['observe','gb010','gb017'],help=argparse.SUPPRESS)
    parser.add_argument('--repeat',type=int,default=1,help=argparse.SUPPRESS)
    parser.add_argument('--artifact-dir',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.headless and args.window_position is not None: parser.error('--window-position requires headed mode')
    if not 30<=args.case_timeout<=180: parser.error('--case-timeout must be 30..180')
    if args.worker:
        if not args.artifact_dir: parser.error('Worker requires artifact directory')
        return worker(args)
    selected=cases()
    run_id=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    batch=EVIDENCE / 'runs' / run_id
    batch.mkdir(parents=True)
    started=time.monotonic()
    summary={'run_id':run_id,'started_at':utc_now(),'mode':'headless' if args.headless else 'headed','requested_window_position':args.window_position,
             'status':'infrastructure_failure','runs':[],'limitations':[
             'Hosted target is unpinned; About version does not identify its exact build.',
             'Only two development cases at Percentage 3 are validated.',
             'Builder protection is allowlisted file tool access; the trusted host is not OS-sandboxed.',
             'No reference source, network response bodies, hidden state, or final evaluation material inspected.']}
    summary['layout_observation']=run_worker(args,'observe',0,batch / 'layout')
    for case in selected:
        for repeat in range(1,4):
            report=run_worker(args,case['case_id'],repeat,batch / f"{case['case_id']}-r{repeat}")
            summary['runs'].append(report)
            write_json(batch / 'summary.json',summary)
            print(f"{case['case_id']} repeat {repeat}: {report['status']}",flush=True)
    groups=[]
    for case in selected:
        rows=[r for r in summary['runs'] if r.get('case_id')==case['case_id']]
        successful=[r for r in rows if 'output' in r]
        hashes=[r['output']['rgba_sha256'] for r in successful]
        agreement=len(hashes)==3 and len(set(hashes))==1
        groups.append({'case_id':case['case_id'],'successful_fresh_exports':len(successful),
            'repeat_rgba_equal':agreement,'reference_equal_all':len(successful)==3 and all(r['reference_comparison']['rgba_equal'] for r in successful)})
    summary['repeat_comparisons']=groups
    if summary['layout_observation']['status']=='passed' and all(r['status']=='passed' for r in summary['runs']) and all(g['repeat_rgba_equal'] for g in groups):
        summary['status']='passed'
    elif all('output' in r for r in summary['runs']):
        summary['status']='reference_mismatch_or_repeat_disagreement'
    summary['finished_at']=utc_now()
    summary['elapsed_seconds']=round(time.monotonic()-started,3)
    write_json(batch / 'summary.json',summary)
    write_json(EVIDENCE / 'latest-batch.json',{'summary_path':str(batch / 'summary.json'),'status':summary['status'],'run_id':run_id})
    print(json.dumps({'status':summary['status'],'summary_path':str(batch / 'summary.json'),'repeat_comparisons':groups},indent=2))
    return 0 if summary['status']=='passed' else 1


if __name__=='__main__':
    sys.exit(main())

"""Reproduce the NEW isolated candidate on 6 visible + 4 final saved cases; no model/browser."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def main():
 bundle=Path(__file__).resolve().parent;source=bundle/'candidate-source';app=ROOT/'generated-app'
 for name,sha in json.loads((bundle/'source-hashes.json').read_text()).items():
  assert hashlib.sha256((source/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==sha,name
 with tempfile.TemporaryDirectory() as temp:
  d=Path(temp);entry=d/'entry.ts';output=d/'batch.mjs'
  entry.write_text('import {applyBrightness} from '+json.dumps((source/'src/brightness.ts').as_posix())+';import {readFileSync} from "node:fs";const rows=JSON.parse(readFileSync(process.argv[2],"utf8"));console.log(JSON.stringify(rows.map(c=>Array.from(applyBrightness({...c.raster,data:new Uint8Array(c.raster.data)},c.brightness).data))));',encoding='utf-8')
  subprocess.run(['node',str(app/'node_modules/esbuild/bin/esbuild'),str(entry),'--bundle','--platform=node','--format=esm','--outfile='+str(output)],check=True)
  rows=[];expected=[]
  for suite in ['visible','final']:
   for c in json.loads((bundle/(suite+'-suite.json')).read_text())['cases']:
    for key in ['input','expected']:
     assert hashlib.sha256((ROOT/c[key]).read_bytes()).hexdigest()==c[key+'_sha256'],c['id']
    im=Image.open(ROOT/c['input']).convert('RGBA');ref=Image.open(ROOT/c['expected']).convert('RGBA');assert im.size==ref.size
    rows.append({'raster':{'width':im.width,'height':im.height,'depth':8,'data':list(im.tobytes())},'brightness':c['brightness']});expected.append(list(ref.tobytes()))
  data=d/'inputs.json';data.write_text(json.dumps(rows),encoding='utf-8')
  result=subprocess.run(['node',str(output),str(data)],capture_output=True,text=True,check=True)
  assert json.loads(result.stdout)==expected,'RGBA mismatch'
  print('10/10 exact RGBA cases reproduced for the isolated clean-start candidate; source/fixture hashes verified; no model/browser calls.')
if __name__=='__main__':main()

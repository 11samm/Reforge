"""Small persisted UI graph; cached navigation is never current behavior evidence."""
import hashlib
import json
import os
import time
from pathlib import Path
from learning.core import save

MAX_BYTES=300000
MAX_NODES=500

def key(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:20]

class InteractionMap:
    def __init__(self,path,target):
        self.path=Path(path); self.target=target; self.target_id=key(target)
        self.data={'schema':1,'target':target,'nodes':{},'routes':{}}
        if self.path.exists():
            if self.path.stat().st_size>MAX_BYTES: raise ValueError('Interaction map size limit')
            loaded=json.loads(self.path.read_text(encoding='utf-8'))
            if loaded.get('schema')!=1 or not isinstance(loaded.get('nodes'),dict) or not isinstance(loaded.get('routes'),dict): raise ValueError('Invalid interaction map')
            if loaded['target']==target: self.data=loaded
        self.session=key([time.time_ns(),str(path)])
        for node in self.data['nodes'].values(): node['status']='stale'
        self.persist()
    def persist(self):
        if len(self.data['nodes'])>MAX_NODES or len(self.data['routes'])>8 or len(json.dumps(self.data).encode())>MAX_BYTES: raise ValueError('Interaction map capacity reached')
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix('.tmp'); save(tmp,self.data); os.replace(tmp,self.path)
    def observe(self,parent,observation_id,controls,source):
        nodes=self.data['nodes']; now=time.time()
        for depth in range(len(parent)):
            prefix=parent[:depth]; prefix_id=key([self.target_id,prefix])
            if prefix_id not in nodes:
                nodes[prefix_id]={'id':prefix_id,'parent':key([self.target_id,prefix[:-1]]) if prefix else None,
                                  'kind':'location','label':prefix[-1]['name'] if prefix else 'Editor',
                                  'navigation':prefix,'status':'visited','last_seen':now,'session':self.session,'evidence':None}
        location_id=key([self.target_id,parent])
        nodes[location_id]={'id':location_id,'parent':key([self.target_id,parent[:-1]]) if parent else None,'kind':'location','label':parent[-1]['name'] if parent else 'Editor',
                            'navigation':parent,'status':'observed','last_seen':now,'session':self.session,'evidence':{'source':source,'observation_id':observation_id}}
        for control in controls:
            label=control.get('label') or (control.get('row') or '').split(':',1)[0] or control.get('text')
            if not label: continue
            role=control.get('role') or {'range':'slider','number':'spinbutton'}.get(control.get('type'),control.get('tag','').lower())
            ident=key([location_id,label,role]); nodes[ident]={'id':ident,'parent':location_id,'kind':'control','label':label,'role':role,
                'dialog':control.get('dialog'),'domain':{k:control.get(k) for k in ('min','max','step')},'observed_value':control.get('value'),
                'status':'observed','last_seen':now,'session':self.session,'evidence':{'source':source,'observation_id':observation_id}}
        self.persist()
    def query(self,query='',parent='',page=0):
        if not isinstance(query,str) or len(query)>160 or not isinstance(parent,str) or len(parent)>40 or type(page) is not int or not 0<=page<=63: raise ValueError('Invalid map query')
        rows=[n for n in self.data['nodes'].values() if (not parent or n['parent']==parent) and (not query or query.casefold() in n['label'].casefold())]
        rows.sort(key=lambda n:(n['kind'],n['label'],n['id']))
        selected=rows[page*8:(page+1)*8]
        return {'kind':'untrusted cached UI navigation, not current reference evidence','target':self.target,'page':page,'pages':max(1,(len(rows)+7)//8),'total':len(rows),'nodes':selected}
    def record_route(self,spec):
        from features.spec import validate
        validate(spec,ready=True)
        if spec['target']!=self.target: raise ValueError('Cached route target differs from map')
        self.data['routes'][spec['feature_id']]={'spec':spec,'observed_at':time.time(),'status':'cached-needs-revalidation'}; self.persist()
    def route(self,feature):
        if not isinstance(feature,str) or feature not in {'contrast'}: raise ValueError('Unsupported cached route')
        row=self.data['routes'].get(feature)
        if not row: return None
        spec=row['spec']
        from features.spec import validate
        validate(spec,ready=True)
        return {'status':row['status'],'observed_at':row['observed_at'],'navigation':spec['navigation'],'dialog':spec['dialog'],
                'controls':[{k:c[k] for k in ('label','type','locator','min','max','step','default')} for c in spec['controls']],
                'apply':spec['apply'],'cancel':spec['cancel'],'instruction':'Replay visible actions and inspect fresh controls; old evidence IDs cannot support this job.'}
    def invalidate_route(self,feature):
        if feature in self.data['routes']: self.data['routes'][feature]['status']='stale'; self.persist()

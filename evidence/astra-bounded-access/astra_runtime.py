"""Reuse verified app-server; no environment tools or raw reasoning persistence."""
import json
import time
from build_shell import FileBroker, ShellRuntime, APP
from smoke import ROOT, safe_error
from .core import KINDS, ROUTES, STATUSES, save

def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
S={'type':'string'}
I={'type':'integer'}
def arr(items): return {'type':'array','items':items}
PLAN=obj({'question':S,'hypotheses':arr(S),'input':obj({'kind':{'type':'string','enum':KINDS},'width':I,'height':I}),
          'percentage':I,'predictions':arr(S),'usefulness':S})
PLANS=obj({'plans':arr(PLAN)})
CLAIM=obj({'id':S,'statement':S,'status':{'type':'string','enum':STATUSES},'target_version':S,
           'setup':S,'parameter_domain':obj({'min':I,'max':I}),'scope':S,
           'supporting_evidence':arr(S),'contradicting_evidence':arr(S),'alternatives':arr(S),
           'unresolved':arr(S),'verification_cases':arr(S)})
CONTRACT=obj({'claims':arr(CLAIM),'decision':S})
ROUTE=obj({'classification':{'type':'string','enum':ROUTES},'evidence_ids':arr(S),'explanation':S,
           'next_action':{'type':'string','enum':['experiment','repair','stop']},'plans':arr(PLAN)})
WRITABLE={'src/main.tsx','src/current-image.ts','src/gaussian-blur.ts','README.md'}

class BlurBroker(FileBroker):
    def __init__(self, journal=None, root=APP, reader=None, allowed_writes=None):
        super().__init__(root)
        self.writable=set(allowed_writes) if allowed_writes is not None else WRITABLE
        if not self.writable <= WRITABLE: raise ValueError('Invalid narrowed write scope')
        self.files=(self.writable | {'src/current-image.ts'}) if allowed_writes is not None else WRITABLE | {'src/style.css'}
        self.journal=journal
        self.reader=reader

    def call(self, tool, args):
        if tool=='evidence_read':
            if self.reader is None: raise ValueError('No evidence reader supplied')
            content=self.reader.call(args)
            self.audit.append({'tool':tool,'arguments':args})
            return content
        result=super().call(tool,args)
        if tool=='shell_write_file' and self.journal is not None:
            self.journal.mkdir(parents=True,exist_ok=True)
            artifact=self.journal/(str(len(self.audit)).zfill(2)+'-'+args['path'].replace('/','_'))
            artifact.write_bytes(self.path(args['path']).read_bytes())
            self.audit[-1]['written_source_artifact']=str(artifact)
        return result

    def path(self,name,write=False):
        if name.startswith('layout-packet/') or (write and name not in getattr(self,'writable',WRITABLE)):
            raise ValueError('Only declared blur application files; packet is supplied in prompt')
        return super().path(name,write)

class NoTools:
    audit=[]
    def call(self,*args): raise ValueError('No tools provided for decision roles')

def invoke(prompt, directory, timeout, schema=None, builder=False, app=APP, reader=None, max_tool_calls=24, allowed_writes=None):
    directory.mkdir(parents=True,exist_ok=False)
    save(directory/'request.json', {'prompt':prompt,'output_schema':schema,'role':'builder' if builder else 'decision',
                                    'app':str(app),'max_tool_calls':max_tool_calls,'allowed_writes':allowed_writes,'deadline_seconds':timeout})
    config=json.loads((ROOT/'smoke.config.json').read_text(encoding='utf-8-sig')); config.update(model='gpt-6-astra',reasoning_effort='medium')
    if (config['model'],config['reasoning_effort']) != ('gpt-6-astra','medium'):
        raise ValueError('Milestone requires verified gpt-6-astra / medium runtime')
    broker=BlurBroker(directory/'written-sources',app,reader,allowed_writes) if builder else NoTools()
    runtime=None; tid=None; started=time.monotonic(); deadline=started+timeout
    report={'status':'failed','model':config['model'],'effort':config['reasoning_effort'],
            'boundary':'environment-disabled; allowlisted broker; trusted host is not OS sandboxed'}
    try:
        runtime=ShellRuntime(config,app,broker); runtime.max_requests=max_tool_calls
        runtime.rpc('initialize',{'clientInfo':{'name':'reforge_learning','version':'0.1.0'},'capabilities':{'experimentalApi':True}},deadline)
        runtime.send({'method':'initialized','params':{}})
        account=runtime.rpc('account/read',{'refreshToken':False},deadline).get('account')
        if not account or account.get('type')!='chatgpt': raise ValueError('Managed ChatGPT login required')
        report['authentication']={'type':'chatgpt','plan':account.get('planType')}
        models=[]; cursor=None
        for _ in range(10):
            page=runtime.rpc('model/list',{'includeHidden':False,'cursor':cursor},deadline)
            models.extend(page['data']); cursor=page.get('nextCursor')
            if not cursor: break
        else: raise ValueError('Catalog pagination budget exhausted')
        chosen=next((m for m in models if m['model']==config['model']),None)
        if not chosen or 'medium' not in [e['reasoningEffort'] for e in chosen['supportedReasoningEfforts']]:
            raise ValueError('Exact model and effort not advertised')
        params={'model':config['model'],'modelProvider':'openai','allowProviderModelFallback':False,
                'cwd':str(app),'runtimeWorkspaceRoots':[str(app)],'approvalPolicy':'never','sandbox':'read-only',
                'ephemeral':True,'environments':[],'selectedCapabilityRoots':[],
                'baseInstructions':'Make bounded evidence-based decisions for miniPaint Gaussian Blur. Do not delegate.',
                'developerInstructions':'No environment, shell, execution, browser, web, plugins, skills or other files. '
                'Use concise decisions and evidence; do not reveal chain-of-thought. Only supplied dynamic tools if present.'}
        if builder:
            params['dynamicTools']=[{'type':'function','name':'shell_read_file','description':'Read declared app source file only.',
                                    'inputSchema':obj({'path':S})},
                                   {'type':'function','name':'shell_write_file','description':'Write declared blur app source file only; no execution.',
                                    'inputSchema':obj({'path':S,'text':S})}]
            if reader is not None:
                from .packets import EVIDENCE_TOOL
                params['dynamicTools'].append(EVIDENCE_TOOL)
        report['thread_start']=params
        thread=runtime.rpc('thread/start',params,deadline)
        if thread['model']!=config['model'] or thread.get('modelProvider')!='openai': raise ValueError('Unexpected runtime model/provider')
        tid=thread['thread']['id']; report['thread_id']=tid
        turn={'threadId':tid,'model':config['model'],'effort':'medium','environments':[],
              'input':[{'type':'text','text':prompt}]}
        if schema: turn['outputSchema']=schema
        runtime.rpc('turn/start',turn,deadline)
        while tid not in runtime.turn_status: runtime.receive(deadline)
        status=runtime.turn_status[tid]['status']; report['completion_status']=status
        items=runtime.completed_items.get(tid,[])
        report['completed_item_types']=[i.get('type') for i in items]
        if status!='completed' or any(i.get('type') not in ['userMessage','agentMessage','reasoning','dynamicToolCall'] for i in items):
            raise ValueError('Incomplete turn or forbidden capability used')
        if any(not r['success'] for r in runtime.requests): raise ValueError('Denied model capability request')
        messages=[i['text'] for i in items if i.get('type')=='agentMessage']
        if not messages: raise ValueError('No completed decision')
        answer=json.loads(messages[-1]) if schema else messages[-1]
        report['answer']=answer; report['status']='passed'
        return answer
    except Exception as error:
        report['error']=safe_error(error)
        raise
    finally:
        if runtime:
            report.update(runtime_version=runtime.version,requests=runtime.requests,audit=broker.audit,
                          usage=runtime.usage.get(tid),runtime_errors=runtime.turn_errors.get(tid,[]))
            runtime.close()
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        save(directory/'invocation.json',report)

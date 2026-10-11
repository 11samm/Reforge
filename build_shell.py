"""Bounded environment-disabled coding invocation through a checked file broker."""
import argparse
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import time
import uuid
from smoke import CodexRuntime, ROOT, safe_error

APP = ROOT / 'generated-app'
PACKET = ROOT / 'evidence/layout-packet'
FILES = {'package.json', 'tsconfig.json', 'index.html', 'src/main.tsx', 'src/current-image.ts', 'src/style.css', 'README.md', 'vite.config.ts'}


class FileBroker:
    def __init__(self, root=APP, packet=PACKET):
        for supplied in (Path(root), Path(packet)):
            for node in [supplied, *supplied.parents]:
                if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
                    raise ValueError('Capability roots cannot contain links or junctions')
        self.root, self.packet = Path(root).resolve(), Path(packet).resolve()
        self.audit = []
        self.files = set(FILES)

    def path(self, name, write=False):
        if not isinstance(name, str) or '\\' in name or ':' in name:
            raise ValueError('Relative forward-slash paths only')
        parts = PurePosixPath(name)
        if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
            raise ValueError('Invalid relative path')
        if name.startswith('layout-packet/'):
            if write or name not in {'layout-packet/observation.md', 'layout-packet/visible-controls.json', 'layout-packet/reference.png'}:
                raise ValueError('Packet is read-only')
            root, target = self.packet, self.packet / name.split('/', 1)[1]
        else:
            if name not in self.files:
                raise ValueError('File outside the application allowlist')
            root, target = self.root, self.root / name
        for node in [target, *target.parents]:
            if node == root.parent:
                break
            if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
                raise ValueError('Links and junctions are forbidden')
        resolved = target.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError('Path escapes permitted root')
        if target.exists() and target.stat().st_nlink > 1:
            raise ValueError('Hard links are forbidden')
        return target

    def call(self, tool, args):
        if not isinstance(args, dict):
            raise ValueError('Expected object')
        if tool == 'shell_write_file' and set(args) == {'path', 'text'}:
            path = self.path(args['path'], write=True)
            if not isinstance(args['text'], str) or len(args['text']) > 80000:
                raise ValueError('File exceeds bound')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args['text'], encoding='utf-8')
            self.audit.append({'tool': tool, 'path': args['path'], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            return [{'type': 'inputText', 'text': 'Saved ' + args['path']}]
        if tool == 'shell_read_file' and set(args) == {'path'}:
            path = self.path(args['path'])
            if path.stat().st_size > 150000:
                raise ValueError('Read exceeds bound')
            self.audit.append({'tool': tool, 'path': args['path']})
            if path.suffix == '.png':
                return [{'type': 'inputImage', 'imageUrl': 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()}]
            return [{'type': 'inputText', 'text': path.read_text(encoding='utf-8')}]
        raise ValueError('Unknown tool or arguments')


class ShellRuntime(CodexRuntime):
    def __init__(self, config, scratch, broker):
        self.broker, self.requests = broker, []
        super().__init__(config, scratch)

    def handle_request(self, message):
        params = message.get('params', {})
        tool = params.get('tool')
        success = False
        try:
            if message['method'] != 'item/tool/call' or len(self.requests) >= getattr(self, 'max_requests', 24):
                raise ValueError('Unexpected request or call limit')
            args = params.get('arguments')
            if isinstance(args, str):
                args = json.loads(args)
            content = self.broker.call(tool, args)
            success = True
        except Exception:
            content = [{'type': 'inputText', 'text': 'Denied: only allowlisted app files, read-only supplied packets/evidence and bounded call counts are accessible; no execution or other tools.'}]
        self.requests.append({'method': message['method'], 'tool': tool, 'success': success})
        if message['method'] == 'item/tool/call':
            self.send({'id': message['id'], 'result': {'success': success, 'contentItems': content}})
        else:
            self.send({'id': message['id'], 'error': {'code': -32601, 'message': 'Denied by shell host'}})


PROMPT = '''Build a fresh independently runnable miniPaint-like editor shell in React + TypeScript + Vite, from the supplied observed layout packet only. First read layout-packet/reference.png and layout-packet/observation.md. Read layout-packet/visible-controls.json if useful. Use shell_write_file for every generated source/config file. All built-in environment, shell, patch, web, connector and delegation capabilities are disabled. Do not attempt other tools.
Allowed output files: package.json, tsconfig.json, index.html, src/main.tsx, src/current-image.ts, src/style.css, README.md, vite.config.ts. Use React 19, React DOM 19, Vite 7, TypeScript 5, fast-png and corresponding @types; minimal setup. Scripts dev (vite --host 127.0.0.1), build (tsc --noEmit && vite build), preview (vite preview --host 127.0.0.1). No lifecycle install scripts. No reference code/assets, remote resources, backend or miniPaint calls. Only one operation placeholder, no filters.
At 1440x1000 faithfully reproduce top dark 30px menu row, 40px options row, 40px left strip, workspace gray, white default 1024x768 canvas centered within workspace at approximately x126 y152, and 200px right column: Preview, Colors, Information, Layer details, Layers. CSS-only approximate icons/color-picker ornament with disabled styling. Preserve dense Arial 13px styling, compact inputs, green accents. Top File menu has functional Open image and Export PNG actions. Other menus/controls must be truly disabled (title unavailable), except Effects can open an accessible Gaussian Blur dialog with disabled Percentage range 0-50 step1 and disabled Apply, clear text unavailable until learning loop implements it, and functional Close. Never implement blur. A clear empty state may be small overlay on default white canvas; do not replace the layout with a large upload landing card. Right Layers must be visible at 1000px height, do not add a new sidebar blur panel that shifts it offscreen.
Functional requirements: upload original PNG/JPEG through labeled file input, validate MIME/signature, reject corrupt/unsupported input visibly with role alert, keep the previous good document on error. Preview as original image object URL, no pixel transformations, no resizing source dimensions. Show native dimensions, one layer named filename, transparency checkerboard. Fit scaling for display only is allowed. PNG export MUST serialize current unpremultiplied RGBA state using the installed fast-png codec, preserving alpha and invisible RGB. Original uploads must still round-trip with exact decoded RGBA; PNG bytes and metadata need not match. No canvas PNG re-encoding. JPEG import may decode at natural dimensions via canvas, then export from the same current RGBA state; document browser decoding/color profile limitations. PNG preview uses img with a useful accessible name such as Original image preview. Export disabled until loaded. Clean object URLs on replacement and unmount, handle rapid replacement with a sequence token. Bound max file size (e.g. 20 MiB), decoded area/dimensions; do not crash on malformed uploads. Disabled controls must remain recognizably styled but unavailable. Include concise startup and limits in README. Do not include tests/evaluator/fixtures in app. You have one bounded turn; generate all files now and briefly confirm.'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repair', help='Concrete build or visual repair instructions; at most two repairs in this milestone')
    args = parser.parse_args()
    config = json.loads((ROOT / 'smoke.config.json').read_text(encoding='utf-8-sig'))
    config['timeout_seconds'] = 180
    run = ROOT / 'evidence/shell-generation' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    broker = FileBroker()
    runtime = None
    report = {'status': 'failed', 'model': config['model'], 'effort': config['reasoning_effort'], 'boundary': 'environment-disabled runtime; allowlisted dynamic file broker; no agent code execution; not an OS sandbox for host process'}
    prompt = PROMPT if not args.repair else 'Repair the existing shell using only shell_read_file and shell_write_file. Read relevant generated files and layout packet. Do not expand scope. ' + args.repair
    (run / 'prompt.txt').write_text(prompt, encoding='utf-8')
    try:
        runtime = ShellRuntime(config, APP, broker)
        runtime.rpc('initialize', {'clientInfo': {'name': 'reforge_shell', 'version': '0.1.0'}, 'capabilities': {'experimentalApi': True}})
        runtime.send({'method': 'initialized', 'params': {}})
        account = runtime.rpc('account/read', {'refreshToken': False}).get('account')
        if not account or account.get('type') != 'chatgpt':
            raise ValueError('Managed ChatGPT login required')
        report['authentication'] = {'type': account['type'], 'plan_type': account.get('planType')}
        models = runtime.rpc('model/list', {'includeHidden': False}).get('data', [])
        model = next((m for m in models if m['model'] == config['model']), None)
        if not model or config['reasoning_effort'] not in [e['reasoningEffort'] for e in model['supportedReasoningEfforts']]:
            raise ValueError('Exact requested model/effort not advertised')
        tools = [{'type': 'function', 'name': 'shell_read_file', 'description': 'Read an allowlisted generated app text file or read-only layout packet file. reference.png returns the reference screenshot.', 'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path'], 'additionalProperties': False}}, {'type': 'function', 'name': 'shell_write_file', 'description': 'Write an allowlisted app file, up to 80000 characters. No other filesystem access or execution.', 'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'text': {'type': 'string'}}, 'required': ['path', 'text'], 'additionalProperties': False}}]
        params = {'model': config['model'], 'modelProvider': 'openai', 'allowProviderModelFallback': False, 'cwd': str(APP), 'runtimeWorkspaceRoots': [str(APP)], 'approvalPolicy': 'never', 'sandbox': 'read-only', 'ephemeral': True, 'environments': [], 'selectedCapabilityRoots': [], 'baseInstructions': 'Build only the requested editor shell. Do not delegate.', 'developerInstructions': 'Only the two supplied dynamic tools are permitted. No shell, environment, other files, web, skills, connectors or reference internals.', 'dynamicTools': tools}
        report['thread_start'] = params
        thread = runtime.rpc('thread/start', params)
        if thread['model'] != config['model'] or thread.get('modelProvider') != 'openai':
            raise ValueError('Unexpected model/provider')
        tid = thread['thread']['id']
        report['thread_id'] = tid
        deadline = time.monotonic() + config['timeout_seconds']
        turn = {'threadId': tid, 'model': config['model'], 'effort': config['reasoning_effort'], 'environments': [], 'input': [{'type': 'text', 'text': prompt}]}
        report['turn_start'] = turn
        runtime.rpc('turn/start', turn, deadline)
        while tid not in runtime.turn_status:
            runtime.receive(deadline)
        status = runtime.turn_status[tid]['status']
        items = runtime.completed_items.get(tid, [])
        types = [item.get('type') for item in items]
        report.update(completion_status=status, completed_item_types=types, usage=runtime.usage.get(tid), requests=runtime.requests, audit=broker.audit, runtime_version=runtime.version)
        report['messages'] = [i['text'] for i in items if i.get('type') == 'agentMessage']
        if status != 'completed' or any(t not in ('userMessage', 'agentMessage', 'reasoning', 'dynamicToolCall') for t in types):
            raise ValueError('Incomplete turn or unexpected capabilities used')
        if not all((APP / p).is_file() for p in ('package.json','tsconfig.json','index.html','src/main.tsx','src/current-image.ts','src/style.css')):
            raise ValueError('Missing generated app files')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = safe_error(error)
    finally:
        if runtime:
            report['requests'], report['audit'] = runtime.requests, broker.audit
            runtime.close()
        (run / 'invocation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'evidence': str(run), 'error': report.get('error')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())

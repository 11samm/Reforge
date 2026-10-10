"""Offline checks of boundaries and protocol failure handling (no inference)."""
from pathlib import Path
import queue
import tempfile
import time
import unittest
from smoke import CodexRuntime, RuntimeErrorCode, validate_answer, validate_source


class SmokeTests(unittest.TestCase):
    def test_structured_response_rejects_bad_types(self):
        good = dict(question='Which boundary rule?', input_description='Bright edge',
                    parameter_value=2, competing_hypotheses=['clamp', 'zero'])
        self.assertEqual(validate_answer(good), good)
        for change in ({'parameter_value': True}, {'parameter_value': float('nan')},
                       {'competing_hypotheses': ['clamp']}, {'question': ''}, {'extra': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_answer(good | change)

    def test_source_cannot_read_files_or_run_external_code(self):
        validate_source('def add(a, b):\n    return a + b\n')
        for source in ('import os\ndef add(a,b): return a+b',
                       'def add(a,b): return open("outside").read()',
                       '@evil\ndef add(a,b): return a+b',
                       'def add(a,b=evil()): return a+b',
                       'def add(a,b): return secret',
                       'def add(a,b):\n while True: pass'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                validate_source(source)

    def bare_runtime(self):
        runtime = CodexRuntime.__new__(CodexRuntime)
        runtime.events = queue.Queue()
        runtime.sequence = 0
        runtime.config = {'rpc_timeout_seconds': 0.02}
        runtime.tool_calls = 0
        runtime.usage, runtime.completed_items, runtime.turn_errors, runtime.turn_status = {}, {}, {}, {}
        runtime.sent = []
        runtime.send = runtime.sent.append
        return runtime

    def test_deadline_and_server_exit(self):
        runtime = self.bare_runtime()
        with self.assertRaises(TimeoutError):
            runtime.receive(time.monotonic() + 0.01)
        runtime.events.put(None)
        with self.assertRaises(RuntimeError):
            runtime.receive(time.monotonic() + 1)

    def test_rpc_error_and_usage_before_response(self):
        runtime = self.bare_runtime()
        runtime.events.put({'method': 'thread/tokenUsage/updated',
                            'params': {'threadId': 't', 'tokenUsage': {'total': {'totalTokens': 5}}}})
        runtime.events.put({'id': 1, 'error': {'code': -123, 'message': 'sensitive text'}})
        with self.assertRaises(RuntimeErrorCode) as error:
            runtime.rpc('model/list', {})
        self.assertEqual(error.exception.code, -123)
        self.assertNotIn('sensitive', str(error.exception))
        self.assertEqual(runtime.usage['t']['total']['totalTokens'], 5)

    def test_file_tool_has_no_path_argument_and_cannot_overwrite(self):
        runtime = self.bare_runtime()
        scratch_root = Path(__file__).parent / '.scratch'
        scratch_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as directory:
            runtime.scratch = Path(directory)
            def call(arguments, tool='create_add_file'):
                runtime.handle_request({'id': 1, 'method': 'item/tool/call',
                                        'params': {'tool': tool, 'arguments': arguments}})
                return runtime.sent[-1]['result']['success']
            self.assertFalse(call({'source': 'def add(a,b): return a+b', 'path': '../escape.py'}))
            self.assertFalse(call({'source': 'def add(a,b): return open("secret").read()'}))
            self.assertFalse(call({}, tool='shell'))
            self.assertTrue(call({'source': 'def add(a,b): return a+b'}))
            self.assertFalse(call({'source': 'def add(a,b): return a-b'}))
            self.assertIn('a+b', (runtime.scratch / 'add.py').read_text())
            self.assertEqual([p.name for p in runtime.scratch.iterdir()], ['add.py'])


if __name__ == '__main__':
    unittest.main()

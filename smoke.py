"""Reforge milestone 1: managed ChatGPT Codex connection, no dataset access."""
import argparse
import ast
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "input_description": {"type": "string"},
        "parameter_value": {"type": "number"},
        "competing_hypotheses": {"type": "array", "items": {"type": "string"}, "minItems": 2},
    },
    "required": ["question", "input_description", "parameter_value", "competing_hypotheses"],
    "additionalProperties": False,
}


def validate_answer(value):
    if not isinstance(value, dict) or set(value) != set(SCHEMA["required"]):
        raise ValueError("Structured answer must have exactly the four required fields")
    for key in ("question", "input_description"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    radius = value["parameter_value"]
    if type(radius) not in (int, float) or not math.isfinite(radius):
        raise ValueError("parameter_value must be a finite number")
    hypotheses = value["competing_hypotheses"]
    if not isinstance(hypotheses, list) or len(hypotheses) < 2 or any(
        not isinstance(x, str) or not x.strip() for x in hypotheses
    ) or len(set(hypotheses)) != len(hypotheses):
        raise ValueError("competing_hypotheses must contain at least two distinct nonempty strings")
    return value


def validate_source(source):
    """Restrict generated code before execution: one pure two-argument function."""
    if not isinstance(source, str) or len(source) > 2000:
        raise ValueError("Source must be a string of at most 2000 characters")
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("Expected only one function")
    fn = tree.body[0]
    args = fn.args
    if fn.name != "add" or fn.decorator_list or fn.returns or fn.type_params or (
        len(args.args) != 2 or args.posonlyargs or args.kwonlyargs or args.vararg
        or args.kwarg or args.defaults or args.kw_defaults
        or any(arg.annotation for arg in args.args)
    ):
        raise ValueError("Expected undecorated add(a, b) without annotations or defaults")
    body = fn.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        raise ValueError("Function must contain only a return expression")
    allowed_names = {x.arg for x in args.args}
    for node in ast.walk(body[0]):
        if not isinstance(node, (ast.Return, ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Name, ast.Load, ast.Constant)):
            raise ValueError("Generated function contains a forbidden expression")
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError("Generated function references an external name")
        if isinstance(node, ast.Constant) and (type(node.value) is not int or abs(node.value) > 1000000):
            raise ValueError("Only small integer constants allowed")
    return source


def safe_error(error):
    # Do not persist raw server messages, which can contain sensitive endpoint data.
    if isinstance(error, (ValueError, TimeoutError, FileNotFoundError)):
        return {"type": type(error).__name__, "message": str(error)}
    return {"type": type(error).__name__, "message": "Runtime/protocol failure; check Codex installation and ChatGPT login"}


class RuntimeErrorCode(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f"RPC failed (code {code})")


class CodexRuntime:
    def __init__(self, config, scratch):
        self.config, self.scratch = config, scratch
        self.events = queue.Queue()
        self.sequence = 0
        self.tool_calls = 0
        self.usage = {}
        self.completed_items = {}
        self.turn_errors = {}
        self.turn_status = {}
        binary = shutil.which(config["codex_bin"])
        if not binary or Path(binary).suffix.lower() in (".cmd", ".bat"):
            raise FileNotFoundError("Set codex_bin to a native Codex executable on PATH or its absolute path")
        self.version = subprocess.check_output([binary, "--version"], timeout=10, text=True, stderr=subprocess.DEVNULL).strip()
        overrides = {
            "model_provider": '"openai"',
            "web_search": '"disabled"',
            "mcp_servers": "{}",
            "features.plugins": "false",
            "features.apps": "false",
            "features.hooks": "false",
            "features.shell_tool": "false",
            "features.multi_agent": "false",
            "features.memories": "false",
            "features.shell_snapshot": "false",
        }
        command = [binary, "app-server", "--listen", "stdio://"]
        for key, value in overrides.items():
            command.extend(["-c", f"{key}={value}"])
        env = os.environ.copy()
        for key in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY"):
            env.pop(key, None)
        self.process = subprocess.Popen(command, cwd=scratch, env=env, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True, encoding="utf-8", bufsize=1,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        try:
            for line in self.process.stdout:
                self.events.put(json.loads(line))
        except Exception:
            pass
        finally:
            self.events.put(None)

    def send(self, value):
        self.process.stdin.write(json.dumps(value) + "\n")
        self.process.stdin.flush()

    def receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Codex execution deadline exceeded")
        try:
            message = self.events.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError("Codex execution deadline exceeded") from None
        if message is None:
            raise RuntimeError("Codex app-server exited unexpectedly")
        if "method" in message and "id" in message:
            self.handle_request(message)
            return {}
        method, params = message.get("method"), message.get("params", {})
        if method == "thread/tokenUsage/updated":
            self.usage[params["threadId"]] = params["tokenUsage"]
        elif method == "item/completed":
            self.completed_items.setdefault(params["threadId"], []).append(params["item"])
        elif method == "error":
            self.turn_errors.setdefault(params.get("threadId"), []).append({
                "willRetry": params.get("willRetry"),
                "code": params.get("error", {}).get("codexErrorInfo"),
            })
        elif method == "turn/completed":
            self.turn_status[params["threadId"]] = params["turn"]
        return message

    def handle_request(self, message):
        if message["method"] != "item/tool/call":
            self.send({"id": message["id"], "error": {"code": -32601, "message": "This smoke client denies all other server requests"}})
            return
        params = message["params"]
        success, result = False, "Only create_add_file is permitted"
        try:
            if params.get("tool") != "create_add_file" or self.tool_calls:
                raise ValueError("Unexpected or repeated tool call")
            arguments = params["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if not isinstance(arguments, dict) or set(arguments) != {"source"}:
                raise ValueError("Tool requires only source")
            source = validate_source(arguments["source"])
            with (self.scratch / "add.py").open("x", encoding="utf-8") as file:
                file.write(source)
            self.tool_calls += 1
            success, result = True, "Created add.py in the isolated scratch workspace"
        except (ValueError, SyntaxError, OSError):
            result = "File rejected: expected a pure add(a, b) function; no imports, calls, annotations, or external names"
        self.send({"id": message["id"], "result": {"success": success,
            "contentItems": [{"type": "inputText", "text": result}]}})

    def rpc(self, method, params, deadline=None):
        self.sequence += 1
        request_id = self.sequence
        self.send({"id": request_id, "method": method, "params": params})
        deadline = deadline or time.monotonic() + self.config["rpc_timeout_seconds"]
        while True:
            message = self.receive(deadline)
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeErrorCode(message["error"].get("code"))
                return message["result"]

    def close(self):
        if self.process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            else:
                self.process.kill()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def run_check(self, model, kind):
        started = time.monotonic()
        deadline = started + self.config["timeout_seconds"]
        result = {"status": "failed", "completion_status": None, "error": None, "usage": None}
        thread_id = None
        try:
            params = {
                "model": model, "modelProvider": "openai", "allowProviderModelFallback": False,
                "cwd": str(self.scratch), "runtimeWorkspaceRoots": [str(self.scratch)],
                "approvalPolicy": "never", "sandbox": "read-only", "ephemeral": True,
                # Disable environment access, so neither shell nor patch/read tools can access data.
                "environments": [], "selectedCapabilityRoots": [],
                "baseInstructions": "You are a coding assistant performing a tiny connectivity check. Follow the requested output format. Do not delegate.",
                "developerInstructions": "Use only the supplied prompt and create_add_file when provided. No filesystem reads, shell, network, skills, connectors, or reference data. Blur behavior is unverified.",
            }
            if kind == "file_edit":
                params["dynamicTools"] = [{"type": "function", "name": "create_add_file",
                    "description": "Create add.py in this check's scratch directory. Accepts only a pure two-argument Python function, no imports or other code.",
                    "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}},
                                    "required": ["source"], "additionalProperties": False}}]
            thread = self.rpc("thread/start", params, deadline)
            thread_id = thread["thread"]["id"]
            result["thread_id"] = thread_id
            result["model"] = thread["model"]
            if thread["model"] != model or thread.get("modelProvider") != "openai":
                raise ValueError("Runtime silently changed the selected model or provider")
            turn_params = {"threadId": thread_id, "model": model,
                           "effort": self.config["reasoning_effort"], "environments": []}
            if kind == "structured_answer":
                prompt = "Propose one diagnostic experiment distinguishing image-blur boundary behavior, e.g. edge replication versus zero padding. Describe a synthetic input and one numeric blur radius. Include at least two competing hypotheses. This is a connectivity proposal, not verified miniPaint behavior. Return only the requested JSON. Do not use tools."
                turn_params["outputSchema"] = SCHEMA
            else:
                prompt = "Use create_add_file to create add.py containing only def add(a, b): returning the sum of the two integers. Do not add annotations or imports. You must call the tool; just printing code is insufficient. Then briefly confirm completion."
            turn_params["input"] = [{"type": "text", "text": prompt}]
            self.rpc("turn/start", turn_params, deadline)
            while thread_id not in self.turn_status:
                self.receive(deadline)
            turn = self.turn_status[thread_id]
            result["completion_status"] = turn["status"]
            if turn["status"] != "completed":
                result["runtime_error_code"] = (turn.get("error") or {}).get("codexErrorInfo")
                raise ValueError("Codex turn did not complete successfully")
            items = self.completed_items.get(thread_id, [])
            result["completed_item_types"] = [item.get("type") for item in items]
            forbidden = [item.get("type") for item in items if item.get("type") not in ("userMessage", "agentMessage", "reasoning", "dynamicToolCall")]
            if forbidden:
                raise ValueError("Unexpected tool use in environment-disabled thread")
            if kind == "structured_answer":
                messages = [item["text"] for item in items if item.get("type") == "agentMessage"]
                result["answer"] = validate_answer(json.loads(messages[-1]))
                result["behavior_verified"] = False
            else:
                if self.tool_calls != 1 or not (self.scratch / "add.py").is_file():
                    raise ValueError("Coding agent did not create add.py through the tool")
                source = validate_source((self.scratch / "add.py").read_text(encoding="utf-8"))
                runner = "import json\n" + source + "\nprint(json.dumps([add(a,b) for a,b in [(2,3),(-7,10),(0,0),(123456,-654321)]]))\n"
                output = subprocess.check_output([sys.executable, "-I", "-S", "-c", runner],
                    cwd=self.scratch, timeout=max(0.01, min(5, deadline - time.monotonic())),
                    text=True, stderr=subprocess.DEVNULL)
                actual = json.loads(output)
                expected = [5, 3, 0, -530865]
                if actual != expected or any(type(x) is not int for x in actual):
                    raise ValueError("Generated add function failed known-input verification")
                result.update({"file": str(self.scratch / "add.py"), "actual": actual, "expected": expected,
                               "agent_tool_calls": self.tool_calls})
            result["status"] = "passed"
        except Exception as error:
            result["error"] = safe_error(error)
            if isinstance(error, RuntimeErrorCode):
                result["rpc_error_code"] = error.code
        finally:
            result["elapsed_seconds"] = round(time.monotonic() - started, 3)
            result["usage"] = self.usage.get(thread_id)
            result["runtime_errors"] = self.turn_errors.get(thread_id, [])
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "smoke.config.json")
    parser.add_argument("--model", help="Explicit model override; never silently substituted")
    args = parser.parse_args()
    started = time.monotonic()
    scratch = ROOT / ".scratch" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    scratch.mkdir(parents=True)
    report = {"runtime": "local Codex app-server (stdio JSON-RPC)", "status": "failed", "checks": {},
              "scratch": str(scratch), "usage_billing": "unknown", "error": None}
    runtime = None
    try:
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        if args.model:
            config["model"] = args.model
        for key in ("timeout_seconds", "rpc_timeout_seconds"):
            if type(config[key]) not in (int, float) or not 1 <= config[key] <= 300:
                raise ValueError(f"{key} must be between 1 and 300 seconds")
        report.update({"requested_model": config["model"], "reasoning_effort": config["reasoning_effort"]})
        runtime = CodexRuntime(config, scratch)
        report["runtime_version"] = runtime.version
        runtime.rpc("initialize", {"clientInfo": {"name": "reforge_smoke", "version": "0.1.0"},
                                  "capabilities": {"experimentalApi": True}})
        runtime.send({"method": "initialized", "params": {}})
        account = runtime.rpc("account/read", {"refreshToken": False}).get("account")
        report["authentication"] = {"type": account.get("type"), "plan_type": account.get("planType")} if account else None
        if not account or account.get("type") != "chatgpt":
            raise ValueError("Managed ChatGPT login required. Run codex login; API billing is disabled for this milestone")
        report["usage_billing"] = "ChatGPT subscription-backed; no API key supplied"
        models, cursor = [], None
        for _ in range(10):
            page = runtime.rpc("model/list", {"includeHidden": False, "cursor": cursor})
            models.extend(page["data"])
            cursor = page.get("nextCursor")
            if not cursor:
                break
        else:
            raise ValueError("Model catalog pagination limit exceeded")
        report["available_models"] = [{"id": m["id"], "model": m["model"],
            "reasoning_efforts": [x["reasoningEffort"] for x in m["supportedReasoningEfforts"]]} for m in models]
        chosen = next((m for m in models if m["model"] == config["model"]), None)
        if not chosen:
            raise ValueError("Requested model is absent from runtime catalog. Choose an advertised coding model explicitly using --model; no automatic fallback")
        if config["reasoning_effort"] not in [x["reasoningEffort"] for x in chosen["supportedReasoningEfforts"]]:
            raise ValueError("Requested reasoning effort is not advertised for the selected model")
        report["exact_model"] = chosen["model"]
        for kind in ("structured_answer", "file_edit"):
            report["checks"][kind] = runtime.run_check(chosen["model"], kind)
            if report["checks"][kind]["error"] and report["checks"][kind]["error"]["type"] in ("TimeoutError", "RuntimeError"):
                break
        if len(report["checks"]) == 2 and all(check["status"] == "passed" for check in report["checks"].values()):
            report["status"] = "passed"
    except Exception as error:
        report["error"] = safe_error(error)
        if isinstance(error, RuntimeErrorCode):
            report["rpc_error_code"] = error.code
    finally:
        if runtime:
            runtime.close()
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        for kind in ("structured_answer", "file_edit"):
            report["checks"].setdefault(kind, {"status": "not_run", "error": "Runtime preflight or execution failed", "usage": None})
        rendered = json.dumps(report, indent=2, allow_nan=False)
        (scratch / "report.json").write_text(rendered + "\n", encoding="utf-8")
        (ROOT / ".scratch" / "latest-report.json").write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

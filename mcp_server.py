#!/usr/bin/env python3
"""
Zen Trails MCP server (stdio / JSON-RPC 2.0).

Bridges MCP tools to the in-game AgentBridge TCP control surface. This lets any
MCP-capable AI agent (including DSH) drive the game with no mouse/keyboard.

Protocol: newline-delimited JSON-RPC 2.0 over stdio.
"""
import json
import sys
import time
import threading
from client import Bridge


# ---- thin JSON-RPC helpers ----

def rpc_result(_id, result):
    return {"jsonrpc": "2.0", "id": _id, "result": result}


def rpc_error(_id, code, message):
    return {"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}}


# ---- bridge connection (lazy, auto-reconnect) ----

class Conn:
    def __init__(self):
        self._b = None
        self._lock = threading.Lock()

    def bridge(self):
        with self._lock:
            if self._b is None:
                self._b = Bridge()
            return self._b

    def call(self, name, *args):
        # retry once if the connection dropped (e.g. game restarted)
        for attempt in (0, 1):
            try:
                b = self.bridge()
                status, out = b.cmd(name, *args)
                return status, out
            except Exception as e:
                if attempt == 0:
                    self._b = None
                    time.sleep(0.5)
                else:
                    return "ERR", f"bridge error: {type(e).__name__}: {e}"
        return "ERR", "unreachable"


conn = Conn()


# ---- tool registry ----

TOOLS = [
    {
        "name": "zen_cmd",
        "description": (
            "Run a raw command on the game's agent bridge (line protocol). "
            "Commands: ping, types <filter>, describe <type>, scene [depth], find <type>, "
            "get <selector> [member.path], set <selector> <member> <value>, "
            "call <selector> <method> [args...], shot <name>, mouse x y act, drag x1 y1 x2 y2 [steps], "
            "clickui <path> [componentType], focus, log [lines]. "
            "selector forms: obj:<instanceID>, path:/Name, type:<FullName> (static singleton or first instance)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "bridge command name"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "positional args"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "zen_screenshot",
        "description": "Capture the game screen to a PNG in <game>/shots/ and return the absolute path.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "file name (no .png)"}},
        },
    },
    {
        "name": "zen_scene",
        "description": "Dump the active scene hierarchy (GameObjects + components) up to a depth.",
        "inputSchema": {
            "type": "object",
            "properties": {"depth": {"type": "integer", "description": "tree depth (default 2)"}},
        },
    },
    {
        "name": "zen_find",
        "description": "List live instances of a Mono/.NET type with instance IDs and scene paths.",
        "inputSchema": {
            "type": "object",
            "properties": {"type": {"type": "string", "description": "type full name or partial"}},
            "required": ["type"],
        },
    },
    {
        "name": "zen_get",
        "description": "Read fields/properties of a resolved object (dot-separated member path).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "members": {"type": "string", "description": "dot path, e.g. length or endPoint.localPosition"},
            },
            "required": ["selector"],
        },
    },
    {
        "name": "zen_call",
        "description": "Invoke a method on a resolved object. Values converted by param type (null for ref types).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "method": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["selector", "method"],
        },
    },
    {
        "name": "zen_describe",
        "description": "Reflect a type: base class, fields, properties, methods, enum values.",
        "inputSchema": {
            "type": "object",
            "properties": {"type": {"type": "string"}},
            "required": ["type"],
        },
    },
    {
        "name": "zen_clickui",
        "description": "Click a Unity UI Button by GameObject path, invoking its onClick in-process (works even when the window is unfocused).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "e.g. Canvas/MainMenu/TutorialButton"},
                "component": {"type": "string", "description": "default UnityEngine.UI.Button"},
            },
            "required": ["path"],
        },
    },
]


def handle_call(name, arguments):
    arguments = arguments or {}
    if name == "zen_cmd":
        command = arguments.get("command")
        args = arguments.get("args") or []
        if not command:
            return rpc_error(None, -32602, "command required")
        status, out = conn.call(command, *args)
        return {"content": [{"type": "text", "text": f"[{status}]\n{out}"}]}

    if name == "zen_screenshot":
        n = arguments.get("name") or ("shot_" + str(int(time.time())))
        status, out = conn.call("shot", n)
        return {"content": [{"type": "text", "text": out if status == "OK" else f"[{status}] {out}"}]}

    if name == "zen_scene":
        depth = arguments.get("depth") or 2
        status, out = conn.call("scene", str(depth))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_find":
        status, out = conn.call("find", arguments.get("type", ""))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_get":
        sel = arguments.get("selector")
        mem = arguments.get("members")
        status, out = conn.call("get", sel) if not mem else conn.call("get", sel, mem)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_call":
        sel = arguments.get("selector")
        method = arguments.get("method")
        args = arguments.get("args") or []
        status, out = conn.call("call", sel, method, *args)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_describe":
        status, out = conn.call("describe", arguments.get("type", ""))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_clickui":
        path = arguments.get("path")
        comp = arguments.get("component")
        status, out = conn.call("clickui", path) if not comp else conn.call("clickui", path, comp)
        return {"content": [{"type": "text", "text": out}]}

    return rpc_error(None, -32601, f"unknown tool {name}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get("method")
        _id = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            resp = rpc_result(_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "zen-trails", "version": "1.0.0"},
            })
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif method == "notifications/initialized" or method == "initialized":
            pass  # notification, no response
        elif method == "tools/list":
            resp = rpc_result(_id, {"tools": TOOLS})
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif method == "tools/call":
            tool = params.get("name")
            args = params.get("arguments") or {}
            try:
                result = handle_call(tool, args)
                resp = rpc_result(_id, result)
            except Exception as e:
                resp = rpc_error(_id, -32603, f"{type(e).__name__}: {e}")
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        elif method == "ping":
            sys.stdout.write(json.dumps(rpc_result(_id, {})) + "\n")
            sys.stdout.flush()
        elif _id is not None:
            sys.stdout.write(json.dumps(rpc_error(_id, -32601, f"unknown method {method}")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

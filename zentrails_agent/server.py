#!/usr/bin/env python3
"""
Zen Trails MCP server (stdio / JSON-RPC 2.0).

Bridges MCP tools to the in-game AgentBridge TCP control surface. This lets any
MCP-capable AI agent (including DSH) drive the game with no mouse/keyboard.

Protocol: newline-delimited JSON-RPC 2.0 over stdio.
"""
import base64
import io
import json
import os
import sys
import time
import threading
from .client import Bridge


# DSH (and MCP in general) speaks UTF-8 over stdio. On Windows the default stdio
# encoding is the ANSI codepage (GBK), which would mangle non-ASCII args/results.
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---- thin JSON-RPC helpers ----

def rpc_result(_id, result):
    return {"jsonrpc": "2.0", "id": _id, "result": result}


def rpc_error(_id, code, message):
    return {"jsonrpc": "2.0", "id": _id, "error": {"code": code, "message": message}}


# ---- bridge connection (lazy, auto-reconnect) ----

class Conn:
    def __init__(self):
        self._b = None
        self._lock = threading.RLock()

    def bridge(self):
        with self._lock:
            if self._b is None:
                self._b = Bridge()
            return self._b

    def call(self, name, *args):
        # 串行化所有调用：单条 TCP 连接不能并发收发，否则响应会交叉错位。
        # 用 RLock 允许 call -> bridge 的嵌套加锁。
        with self._lock:
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

NAMED_COLORS = {
    "gold": "1.00,0.85,0.28,1",
    "cyan": "0.20,0.92,1.00,1",
    "magenta": "1.00,0.25,0.58,1",
    "violet": "0.78,0.32,1.00,1",
    "amber": "1.00,0.60,0.15,1",
    "white": "1.00,0.98,0.90,1",
    "rose": "1.00,0.20,0.50,1",
    "aqua": "0.25,1.00,0.85,1",
    "red": "1.00,0.15,0.15,1",
    "blue": "0.15,0.40,1.00,1",
    "green": "0.20,0.95,0.30,1",
}

_next_segment_id = 1000


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
        "description": (
            "Capture the game screen to a PNG in <game>/shots/ and return the absolute path. "
            "Set return_image=true to also return the image inline (base64, scaled to max 1280px wide) "
            "so a vision-capable model can see it directly."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "file name (no .png)"},
                "return_image": {"type": "boolean", "description": "inline the image as base64 content"},
            },
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
        "name": "zen_types",
        "description": "List game types (from loaded non-System assemblies), optionally filtered by a name substring.",
        "inputSchema": {
            "type": "object",
            "properties": {"filter": {"type": "string", "description": "substring match (empty = all)"}},
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
        "name": "zen_set",
        "description": (
            "Write a field/property of a resolved object. Value is converted by the member's declared type "
            "(e.g. '1.5' for float, 'true' for bool, '1,0.5,0,1' for Color/Vector)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"},
                "member": {"type": "string", "description": "member name or dot path (leaf is written)"},
                "value": {"type": "string"},
            },
            "required": ["selector", "member", "value"],
        },
    },
    {
        "name": "zen_call",
        "description": (
            "Invoke a method on a resolved object. Values converted by param type (null for ref types). "
            "For methods returning IEnumerator (coroutines), use zen_coroutine instead so it actually runs."
        ),
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
        "name": "zen_coroutine",
        "description": (
            "Invoke a coroutine method (returns IEnumerator) on a MonoBehaviour and start it via StartCoroutine, "
            "so the game's own frame loop runs it."
        ),
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
    {
        "name": "zen_music",
        "description": "Switch background music. Tracks: Mandalas, Wavelengths, Footprints, Dreams, Space. Omit song to play next track.",
        "inputSchema": {
            "type": "object",
            "properties": {"song": {"type": "string", "description": "track name, or omit for next"}},
        },
    },
    {
        "name": "zen_save",
        "description": "Save the current artwork to a .mndla save file (BinaryFormatter). type: 'custom' (normal) or 'preset'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string", "description": "custom (default) | preset"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "zen_load",
        "description": "Load a .mndla save file by name (deserialize + call SaveAndLoadManager.Load). type: 'custom' | 'preset'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string", "description": "custom (default) | preset"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "zen_upload",
        "description": (
            "Upload the saved design to Steam Workshop. Requires Steam connected, an existing save, "
            "and a title. Real network side effect: publishes publicly. Optional description, then "
            "takes a thumbnail screenshot and uploads. Returns the uploader's status text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title"],
        },
    },
    # ---- High-Level Domain Tools for AI Creators ----
    {
        "name": "zen_create_segment",
        "description": (
            "High-level tool to create a new moving pendulum segment with light trails. "
            "Handles ID generation, parameter formatting, and hides physical arm meshes automatically. "
            "Set parent_id to chain segments into harmonic epicycles (rosettes, stars, mandalas)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "description": "Arm length (e.g. 1.5, 2.5)."},
                "speed": {"type": "number", "description": "Angular velocity. Positive = clockwise, negative = counter-clockwise, 0 = stationary anchor."},
                "angle": {"type": "number", "description": "Initial starting angle in degrees (default 0.0)."},
                "parent_id": {"type": ["integer", "null"], "description": "Parent segment ID to attach to. null = root attached to origin (0,0)."},
                "color": {"type": "string", "description": "RGBA 'r,g,b,a' (0~1) or color name: gold, cyan, magenta, violet, amber, white, rose, aqua, red, green, blue (default 'gold')."},
                "width": {"type": "number", "description": "Trail ribbon width (default 0.40)."},
                "glow": {"type": "number", "description": "Glow bloom intensity (default 1.8)."},
                "draw_trail": {"type": "boolean", "description": "True to draw glowing light trail, False for invisible support/carrier arms (default true)."},
                "hide_mesh": {"type": "boolean", "description": "Hide physical mechanical arm meshes to show pure celestial trails (default true)."},
                "id": {"type": "integer", "description": "Optional custom segment ID (auto-assigned if omitted)."},
            },
            "required": ["length", "speed"],
        },
    },
    {
        "name": "zen_clear",
        "description": "Clear the entire canvas safely. Deletes all active segments and resets state for a new creation.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "zen_play",
        "description": "Start or resume physics simulation to begin drawing glowing light trails.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "zen_pause",
        "description": "Safely freeze the simulation with TogglePause. Preserves all drawn light trails in place without erasing.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "zen_dark_mode",
        "description": "Switch to pure cosmic dark mode: disables distracting background animations and sets camera background to deep cosmic black.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "Background RGBA color (default '0.02,0.02,0.04,1')."},
            },
        },
    },
    {
        "name": "zen_set_camera",
        "description": "Position camera view distance. Recommended: z=-10.5 for medium mandalas (R<=3.5), z=-12.8 for grand multi-circle matrix (R>4.5).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "distance": {"type": "number", "description": "Camera Z distance (negative, default -12.5)."},
                "x": {"type": "number", "description": "Camera X position (default 0.0)."},
                "y": {"type": "number", "description": "Camera Y position (default 0.0)."},
            },
        },
    },
    {
        "name": "zen_hide_arms",
        "description": "Toggle visibility of physical mechanical arm linkages. When hidden, only pure glowing trails are visible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hide": {"type": "boolean", "description": "Whether to hide physical arm meshes (default true)."},
            },
        },
    },
    {
        "name": "zen_list_segments",
        "description": "List all active segments in the current artwork with their IDs, parent links, lengths, speeds, and colors.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def _inline_image(path, max_width=1280):
    """Read a screenshot and return an MCP image content block (JPEG, scaled)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    if not os.path.isfile(path):
        return None
    try:
        im = Image.open(path).convert("RGB")
        if im.width > max_width:
            h = max(1, int(im.height * max_width / im.width))
            im = im.resize((max_width, h))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=82)
        return {"type": "image", "data": base64.b64encode(buf.getvalue()).decode("ascii"), "mimeType": "image/jpeg"}
    except Exception:
        return None


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
        if n.lower().endswith(".png"):
            n = n[:-4]
        status, out = conn.call("shot", n)
        if status != "OK":
            return {"content": [{"type": "text", "text": f"[{status}] {out}"}]}
        path = out.strip()
        # ScreenCapture writes at end of frame; poll until the file exists
        for _ in range(50):
            st, info = conn.call("bytes", path)
            if st == "OK" and "size=" in info and info.split("size=")[1].split()[0] != "0":
                break
            time.sleep(0.1)
        content = [{"type": "text", "text": path}]
        if arguments.get("return_image"):
            img = _inline_image(path)
            if img is not None:
                content.insert(0, img)
        return {"content": content}

    if name == "zen_scene":
        depth = arguments.get("depth") or 2
        status, out = conn.call("scene", str(depth))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_find":
        status, out = conn.call("find", arguments.get("type", ""))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_types":
        status, out = conn.call("types", arguments.get("filter", ""))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_get":
        sel = arguments.get("selector")
        mem = arguments.get("members")
        status, out = conn.call("get", sel) if not mem else conn.call("get", sel, mem)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_set":
        sel = arguments.get("selector")
        member = arguments.get("member")
        value = arguments.get("value")
        if not member or value is None:
            return {"content": [{"type": "text", "text": "selector, member and value are required"}]}
        status, out = conn.call("set", sel, member, value)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_call":
        sel = arguments.get("selector")
        method = arguments.get("method")
        args = arguments.get("args") or []
        status, out = conn.call("call", sel, method, *args)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_coroutine":
        sel = arguments.get("selector")
        method = arguments.get("method")
        args = arguments.get("args") or []
        status, out = conn.call("coroutine", sel, method, *args)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_describe":
        status, out = conn.call("describe", arguments.get("type", ""))
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_clickui":
        path = arguments.get("path")
        comp = arguments.get("component")
        status, out = conn.call("clickui", path) if not comp else conn.call("clickui", path, comp)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_music":
        song = arguments.get("song")
        if song:
            status, out = conn.call("call", "type:MusicManager", "PlaySpecificSong", song)
        else:
            status, out = conn.call("call", "type:MusicManager", "NextSong")
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_save":
        name_ = arguments.get("name")
        typ = arguments.get("type") or "custom"
        status, out = conn.call("call", "type:SaveAndLoadManager", "Save", name_, typ)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_load":
        name_ = arguments.get("name")
        typ = arguments.get("type") or "custom"
        status, out = conn.call("loadsave", name_, typ)
        return {"content": [{"type": "text", "text": out}]}

    if name == "zen_upload":
        title = arguments.get("title", "")
        desc = arguments.get("description", "")
        if not title:
            return {"content": [{"type": "text", "text": "title required"}]}

        # 1. 确保画面处于运行并绘出流光轨迹的状态：
        # 游戏中的 TrailRenderer 只在运转时产生轨迹。若处于刚加载的静态编辑态（sequencing=false），
        # 画面上没有任何流光，必须先启动运转让轨迹画满，并用 TogglePause 定格，才能截取到真实绚烂的画面。
        st_seq, out_seq = conn.call("get", "type:ClickAndDrag", "sequencing")
        if "False" in out_seq:
            conn.call("set", "type:ClickAndDrag", "paused", "false")
            conn.call("call", "type:ClickAndDrag", "StartOrStop")
            time.sleep(18.0)
            conn.call("call", "type:ClickAndDrag", "TogglePause")
            time.sleep(0.8)

        # 2. 打开 Uploader 面板并等待其展开动效彻底就绪
        # OpenWithCurtain.Open() 包含展开动画，等待 1.8 秒以确保面板完全撑开、Curtain 幕布完全收起。
        conn.call("call", "type:Uploader", "Open")
        time.sleep(1.8)

        st, out = conn.call("get", "type:Uploader", "designTitle")
        tid = out.split("id=")[1].split(")")[0]
        conn.call("set", f"obj:{tid}", "text", title)
        if desc:
            st, out = conn.call("get", "type:Uploader", "description")
            did = out.split("id=")[1].split(")")[0]
            conn.call("set", f"obj:{did}", "text", desc)

        # 3. 核心机制：触发上传面板上的官方「截图」按钮
        # 游戏原生 Uploader.ieTakeScreenshot 协程在面板完全展开后调用，
        # 会精确自动隐藏右上角导航栏（sNavPanel.gameObject.SetActive(false)）、自身弹窗及所有设置面板，
        # 截取纯净无任何多余 UI 按钮的游戏主视口，并自动编码为 PreviewImage.jpg 供上传。
        conn.call("clickui", "Canvas/Uploader/AddScreenshotButton/Button")
        # 等待截图协程完成（包含 WaitForEndOfFrame + 1.0s WaitForSeconds 编码写盘）
        time.sleep(2.5)

        # 4. 提交上传
        st, out = conn.call("call", "type:Uploader", "Upload")
        st2, status_obj = conn.call("get", "type:Uploader", "statusText")
        status_txt = status_obj
        if "id=" in status_obj:
            sid = status_obj.split("id=")[1].split(")")[0]
            st3, status_txt = conn.call("get", f"obj:{sid}", "text")
        return {"content": [{"type": "text", "text": f"{out}\nstatus: {status_txt}"}]}

    # ---- High-Level Domain Tools Handlers ----
    global _next_segment_id

    if name == "zen_create_segment":
        length = float(arguments.get("length", 1.0))
        speed = float(arguments.get("speed", 1.0))
        angle = float(arguments.get("angle", 0.0))
        parent_id = arguments.get("parent_id")
        color_arg = arguments.get("color", "gold")
        color = NAMED_COLORS.get(str(color_arg).lower(), str(color_arg))
        width = float(arguments.get("width", 0.40))
        glow = float(arguments.get("glow", 1.8))
        draw_trail = bool(arguments.get("draw_trail", True))
        hide_mesh = bool(arguments.get("hide_mesh", True))
        custom_id = arguments.get("id")

        if custom_id is not None:
            sid = int(custom_id)
            if sid >= _next_segment_id:
                _next_segment_id = sid + 1
        else:
            sid = _next_segment_id
            _next_segment_id += 1

        is_child = "1" if (parent_id is not None and str(parent_id).lower() != "null") else "0"
        parent_str = str(parent_id) if (parent_id is not None and str(parent_id).lower() != "null") else "null"

        args = [
            is_child,
            str(sid),
            parent_str,
            f"{length:.4f}",
            f"{speed}",
            f"{angle:.2f}",
            "1" if draw_trail else "0",
            f"{width:.2f}",
            str(color),
            "0,0,0",
            "0",
            f"{glow:.2f}",
            "0",
            "null",
            "0",
            "0"
        ]
        st, out = conn.call("call", "type:ClickAndDrag", "CreateNewSegment", *args)
        if hide_mesh:
            conn.call("set", "path:/ClickAndDragMaster/Segment(Clone)", "hideMesh", "true")
        return {"content": [{"type": "text", "text": f"Created segment ID={sid} (length={length}, speed={speed}, angle={angle}, parent={parent_str}, trail={draw_trail})"}]}

    if name == "zen_clear":
        conn.call("set", "type:ClickAndDrag", "paused", "false")
        st, out = conn.call("call", "type:ClickAndDrag", "DeleteAll")
        _next_segment_id = 1000
        return {"content": [{"type": "text", "text": "Canvas cleared. All segments deleted."}]}

    if name == "zen_play":
        conn.call("set", "type:ClickAndDrag", "paused", "false")
        st, out_seq = conn.call("get", "type:ClickAndDrag", "sequencing")
        if "False" in out_seq:
            conn.call("call", "type:ClickAndDrag", "StartOrStop")
        return {"content": [{"type": "text", "text": "Simulation running. Drawing light trails."}]}

    if name == "zen_pause":
        st, out_seq = conn.call("get", "type:ClickAndDrag", "sequencing")
        if "True" in out_seq:
            conn.call("call", "type:ClickAndDrag", "TogglePause")
        return {"content": [{"type": "text", "text": "Simulation paused. Light trails frozen in place without erasing."}]}

    if name == "zen_dark_mode":
        bg_col = arguments.get("color", "0.02,0.02,0.04,1")
        st, out = conn.call("find", "Background")
        if st == "OK" and len(out.splitlines()) > 1:
            oid = out.splitlines()[1].split()[1]
            st, bg = conn.call("get", f"obj:{oid}", "currentBG")
            if "id=" in bg:
                bg_id = bg.strip().split("id=")[1].rstrip(")")
                conn.call("call", f"obj:{bg_id}", "SetActive", "false")
        st, out = conn.call("find", "Camera")
        if st == "OK" and len(out.splitlines()) > 1:
            cam = out.splitlines()[1].split()[1]
            conn.call("set", f"obj:{cam}", "backgroundColor", bg_col)
            conn.call("set", f"obj:{cam}", "clearFlags", "SolidColor")
        return {"content": [{"type": "text", "text": f"Dark mode activated. Background color set to {bg_col}."}]}

    if name == "zen_set_camera":
        dist = arguments.get("distance", -12.5)
        x = arguments.get("x", 0.0)
        y = arguments.get("y", 0.0)
        conn.call("set", "type:CameraPosition", "targetPos", f"{x},{y},{dist}")
        return {"content": [{"type": "text", "text": f"Camera positioned at ({x}, {y}, {dist})."}]}

    if name == "zen_hide_arms":
        hide = bool(arguments.get("hide", True))
        conn.call("set", "type:SettingsPanel", "hideSegments", "true" if hide else "false")
        return {"content": [{"type": "text", "text": f"Physical arm meshes {'hidden' if hide else 'shown'}."}]}

    if name == "zen_list_segments":
        st, segs = conn.call("get", "type:ClickAndDrag", "segments")
        if "Count = 0" in segs or "segments = []" in segs:
            return {"content": [{"type": "text", "text": "No segments active on canvas."}]}
        ids = [part.split(')')[0] for part in segs.split('Segment(Clone)(id=')[1:]]
        lines = [f"Active segments count: {len(ids)}"]
        for oid in ids:
            st, sid_ = conn.call("get", f"obj:{oid}", "ID")
            st, pid_ = conn.call("get", f"obj:{oid}", "parentID")
            st, len_ = conn.call("get", f"obj:{oid}", "length")
            st, spd_ = conn.call("get", f"obj:{oid}", "speed")
            st, ang_ = conn.call("get", f"obj:{oid}", "angle")
            st, tr_ = conn.call("get", f"obj:{oid}", "drawTrail")
            st, col_ = conn.call("get", f"obj:{oid}", "color")
            lines.append(f"  - ID={sid_.split('=')[1].strip()} Parent={pid_.split('=')[1].strip()} Length={len_.split('=')[1].strip()} Speed={spd_.split('=')[1].strip()} Angle={ang_.split('=')[1].strip()} Trail={tr_.split('=')[1].strip()} Color={col_.split('=')[1].strip()}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

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

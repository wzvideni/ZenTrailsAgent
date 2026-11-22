"""打发布包：编译插件 + 组装 MCP 服务 + 安装说明，压成可直接分发的 zip。

产物结构（zip 内）：
    ZenTrails-AI控制-v<版本>/
        安装说明.txt
        game/                          ← 解压覆盖到游戏根目录
            winhttp.dll
            doorstop_config.ini
            .doorstop_version
            BepInEx/core/              ← BepInEx 5 运行时
            BepInEx/plugins/ZenTrailsAgent.dll
        mcp/                           ← MCP 服务，放任意目录，用 uvx 启动
            pyproject.toml
            zentrails_agent/…
            client.py  mcp_server.py

用法（仓库根目录执行）：
    uv run python tools/package.py                 # 编译插件 + 组装 + 打 zip
    uv run python tools/package.py --no-rebuild     # 用已有 dist/ZenTrailsAgent.dll，不重编
    uv run python tools/package.py --game <路径>    # 指定游戏目录（默认 ZEN_TRAILS_HOME / Steam 常见位置）

运行时文件（winhttp.dll、doorstop、BepInEx core）从游戏目录原样取，所以打出来的包
与目标游戏运行时一致；MCP 服务代码从仓库 zentrails_agent/ 现取，与源码一致。
"""
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import paths  # noqa: E402

import argparse
import shutil
import subprocess
import zipfile

# 从游戏目录原样带走的运行时文件（BepInEx 5 加载器 + 本体）
RUNTIME_TOP = ["winhttp.dll", "doorstop_config.ini", ".doorstop_version"]
RUNTIME_DIRS = ["BepInEx/core"]

# MCP 服务：仓库内要一起打包的文件/目录（相对仓库根）
MCP_FILES = [
    "pyproject.toml",
    "zentrails_agent",
    "client.py",
    "mcp_server.py",
]

# 打包时给 mcp/ 生成的精简 pyproject（去掉 readme 引用，因为 mcp/ 目录内不放长 README）
MCP_PYPROJECT = """[project]
name = "zen-trails-agent"
version = "{version}"
description = "Zen Trails AI 控制：BepInEx 进程内注入 + MCP 工具，让 AI Agent 驱动游戏"
requires-python = ">=3.11"
dependencies = [
    "pillow>=10.0",
]

[project.scripts]
zen-trails-agent = "zentrails_agent.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["zentrails_agent"]
"""


# 控制台/管道按 UTF-8 输出，避免中文在 GBK 终端里变乱码
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _version():
    """从 zentrails_agent/__init__.py 读 __version__。"""
    import re
    p = _os.path.join(paths.PKG, "__init__.py")
    txt = open(p, encoding="utf-8").read()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', txt)
    if not m:
        raise SystemExit("读不到 __version__：%s" % p)
    return m.group(1)


def log(msg):
    print(msg, flush=True)


def need(path):
    if not _os.path.exists(path):
        raise SystemExit("缺少 %s（游戏目录可用 --game 或 ZEN_TRAILS_HOME 指定）" % path)
    return path


def copy_tree(src, dst):
    if _os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        _os.makedirs(_os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def _ps():
    """返回可用的 PowerShell：优先 pwsh（PowerShell 7，默认 UTF-8），回退 powershell。"""
    for name in ("pwsh", "powershell"):
        if shutil.which(name):
            return name
    return "powershell"


def build_plugin(game, out_dll):
    """编译 AgentBridge.cs → dist/ZenTrailsAgent.dll。"""
    log("· 编译插件")
    subprocess.run(
        [_ps(), "-ExecutionPolicy", "Bypass", "-File",
         _os.path.join(paths.TOOLS, "build_plugin.ps1"), "-Game", game],
        check=True,
    )
    need(out_dll)


def stage_runtime(game, stage):
    """从游戏目录收集 BepInEx 运行时 + 加载器，放到 staging 的 game/ 子目录。"""
    gdir = _os.path.join(stage, "game")
    _os.makedirs(gdir, exist_ok=True)
    for name in RUNTIME_TOP:
        copy_tree(need(_os.path.join(game, name)), _os.path.join(gdir, name))
    for name in RUNTIME_DIRS:
        copy_tree(need(_os.path.join(game, name)), _os.path.join(gdir, name))
    # 插件 DLL 也放 game/BepInEx/plugins/
    copy_tree(_os.path.join(paths.DIST, "ZenTrailsAgent.dll"),
              _os.path.join(gdir, "BepInEx/plugins/ZenTrailsAgent.dll"))


def stage_mcp(stage, version):
    """把 MCP 服务（Python 包）放进 staging 的 mcp/ 子目录。"""
    mdir = _os.path.join(stage, "mcp")
    _os.makedirs(mdir, exist_ok=True)
    # 用精简 pyproject 覆盖（版本号动态写入，去掉 readme 引用）
    with open(_os.path.join(mdir, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(MCP_PYPROJECT.format(version=version))
    for name in ("zentrails_agent", "client.py", "mcp_server.py"):
        copy_tree(_os.path.join(paths.ROOT, name), _os.path.join(mdir, name))
    # 剔除 __pycache__，避免把本机字节码打进发布包
    for dirpath, dirnames, _ in _os.walk(mdir):
        if "__pycache__" in dirnames:
            shutil.rmtree(_os.path.join(dirpath, "__pycache__"))


def make_zip(stage, zip_path):
    """按路径排序写 zip（与 .NET CreateFromDirectory 一致：不写目录条目）。"""
    entries = []
    for dirpath, _, filenames in _os.walk(stage):
        for fn in filenames:
            full = _os.path.join(dirpath, fn)
            entries.append((_os.path.relpath(full, stage).replace(_os.sep, "/"), full))
    entries.sort()
    if _os.path.exists(zip_path):
        _os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, full in entries:
            z.write(full, name)
    return len(entries)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=paths.GAME)
    ap.add_argument("--no-rebuild", action="store_true",
                    help="用已有 dist/ZenTrailsAgent.dll，不重新编译")
    args = ap.parse_args()

    version = _version()
    out_dll = paths.PLUGIN_DLL

    if args.no_rebuild:
        need(out_dll)
        log("· 用已有 %s（要重编去掉 --no-rebuild）" % out_dll)
    else:
        build_plugin(args.game, out_dll)

    top = "ZenTrails-AI控制-v%s" % version
    stage = _os.path.join(paths.DIST, "_stage")
    if _os.path.isdir(stage):
        shutil.rmtree(stage)
    _os.makedirs(stage, exist_ok=True)

    stage_runtime(args.game, stage)
    stage_mcp(stage, version)

    # 安装说明
    doc = _os.path.join(paths.DOCS, "安装说明.txt")
    need(doc)
    copy_tree(doc, _os.path.join(stage, "安装说明.txt"))

    files = sum(len(f) for _, _, f in _os.walk(stage))
    size = sum(_os.path.getsize(_os.path.join(d, f))
               for d, _, fs in _os.walk(stage) for f in fs)
    log("· 组装完成：%d 个文件，%.1f MB" % (files, size / 1048576.0))

    # 打 zip：顶层是 ZenTrails-AI控制-v<版本>/ 目录
    zip_path = _os.path.join(paths.DIST, "%s.zip" % top)
    # 先把 staging 内容整体放进 top/ 再压，使解压后是一个顶层目录
    wrap = _os.path.join(paths.DIST, "_wrap")
    if _os.path.isdir(wrap):
        shutil.rmtree(wrap)
    _os.makedirs(wrap, exist_ok=True)
    shutil.copytree(stage, _os.path.join(wrap, top))
    n = make_zip(wrap, zip_path)
    shutil.rmtree(wrap, ignore_errors=True)
    shutil.rmtree(stage, ignore_errors=True)

    log("· 打包完成：%s（%d 条目，%.1f MB）"
        % (zip_path, n, _os.path.getsize(zip_path) / 1048576.0))


if __name__ == "__main__":
    main()

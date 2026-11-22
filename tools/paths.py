"""统一的路径约定。

仓库内的目录一律以本文件为基准（纯相对定位，整个仓库可以随意搬动）；
游戏安装目录在仓库之外，用环境变量 ZEN_TRAILS_HOME 覆盖，默认按 Steam 的常见安装位置拼出来。
"""
import os

# ---------- 仓库内（相对本文件） ----------
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SRC = os.path.join(ROOT, "src")                 # C# 插件源码
PKG = os.path.join(ROOT, "zentrails_agent")     # Python 包（MCP server + client）
DOCS = os.path.join(ROOT, "docs")               # 安装说明等
DIST = os.path.join(ROOT, "dist")               # 编译产物 + 发布包
DUMPS = os.path.join(ROOT, "dumps")             # 逆向中间产物

# ---------- 游戏安装目录（仓库外，可用环境变量覆盖） ----------
GAME = os.environ.get("ZEN_TRAILS_HOME") or os.path.join(
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
    "Steam", "steamapps", "common", "Zen Trails",
)

BEPINEX = os.path.join(GAME, "BepInEx")
PLUGINS = os.path.join(BEPINEX, "plugins")
CORE = os.path.join(BEPINEX, "core")
MANAGED = os.path.join(GAME, "Zen Trails_Data", "Managed")

# 插件编译产物
PLUGIN_DLL = os.path.join(DIST, "ZenTrailsAgent.dll")


def has_game():
    """游戏目录在不在（脚本里做前置检查用）。"""
    return os.path.isdir(GAME)


if __name__ == "__main__":
    for k in ("ROOT", "SRC", "PKG", "DIST", "GAME", "PLUGINS"):
        print("%-10s %s" % (k, globals()[k]))
    print("%-10s %s" % ("game ok", has_game()))

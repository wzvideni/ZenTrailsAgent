"""暗色模式：关闭背景贴图层 + 相机纯色背景（适合观察轨迹颜色）。

用法：
    python tools/dark_mode.py            # 开启暗色模式（默认深灰蓝）
    python tools/dark_mode.py 0.05,0.05,0.08,1   # 自定义颜色
    python tools/dark_mode.py restore    # 恢复游戏背景
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import Bridge


def dark(b, color="0.10,0.10,0.14,1"):
    st, out = b.cmd("find", "Background")
    oid = out.splitlines()[1].split()[1]
    st, out = b.cmd("get", f"obj:{oid}", "currentBG")
    bg_id = out.strip().split("id=")[1].rstrip(")")
    print("关闭背景层:", b.cmd("call", f"obj:{bg_id}", "SetActive", "false")[1].strip())
    st, out = b.cmd("find", "Camera")
    cam = out.splitlines()[1].split()[1]
    print("背景色:", b.cmd("set", f"obj:{cam}", "backgroundColor", color)[1].strip())
    print("清屏:", b.cmd("set", f"obj:{cam}", "clearFlags", "SolidColor")[1].strip())


def restore(b):
    st, out = b.cmd("find", "Background")
    oid = out.splitlines()[1].split()[1]
    st, out = b.cmd("get", f"obj:{oid}", "currentBG")
    bg_id = out.strip().split("id=")[1].rstrip(")")
    print("恢复背景层:", b.cmd("call", f"obj:{bg_id}", "SetActive", "true")[1].strip())
    st, out = b.cmd("find", "Camera")
    cam = out.splitlines()[1].split()[1]
    print("清屏:", b.cmd("set", f"obj:{cam}", "clearFlags", "Skybox")[1].strip())


if __name__ == "__main__":
    b = Bridge()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "restore":
        restore(b)
    else:
        dark(b, arg or "0.10,0.10,0.14,1")
    b.close()

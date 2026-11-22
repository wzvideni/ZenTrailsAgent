"""相机控制：缩放 / 平移 / 居中。

targetPos 是 CameraPosition 的静态字段：x/y 平移、z 缩放（负值，越负越远）。
范围：z ∈ [-30, 0]（maxZoomDist=30），x/y ∈ [-20, 20]（maxDist=20）。
相机平滑过渡到目标值，命令返回后约 1-2 秒到位。

用法：
    python tools/camera.py zoom -10.5        # 设置缩放（仅改 z）
    python tools/camera.py pan 3 2           # 平移（仅改 x/y）
    python tools/camera.py center            # 居中 z=-10.5
    python tools/camera.py center -6         # 居中并拉近
    python tools/camera.py get               # 读当前 targetPos
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client import Bridge


def get_target(b):
    st, out = b.cmd("get", "type:CameraPosition", "targetPos")
    m = re.search(r"\(([^)]+)\)", out)
    if not m:
        raise RuntimeError(f"cannot parse targetPos: {out!r}")
    x, y, z = (float(v) for v in m.group(1).split(","))
    return x, y, z


def main():
    b = Bridge()
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "get"):
        x, y, z = get_target(b)
        print(f"targetPos = ({x}, {y}, {z})")
        if not args:
            print(__doc__)
        b.close()
        return

    x, y, z = get_target(b)
    cmd = args[0]
    if cmd == "zoom":
        z = float(args[1])
        new = f"{x},{y},{z}"
    elif cmd == "pan":
        x, y = float(args[1]), float(args[2])
        new = f"{x},{y},{z}"
    elif cmd == "center":
        z = float(args[1]) if len(args) > 1 else -10.5
        new = f"0,0,{z}"
    else:
        print(__doc__)
        b.close()
        return
    print(b.cmd("set", "type:CameraPosition", "targetPos", new)[1].strip())
    b.close()


if __name__ == "__main__":
    main()

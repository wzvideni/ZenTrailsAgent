"""魔法阵 v5 —— 标准外摆线花瓣（epicycloid），层次分明的六芒星魔法阵。

外摆线条件（推导）：
  P(t) = R1·e^{iωt} + R2·e^{i(1+s)ωt}
  匹配 epicycloid P = (R+r)e^{iθ} - r·e^{i(R+r)/r·θ} 需要：
    R1 = R+r, R2 = r 且子向量反向 -> 子初始角 180°
    (1+s) = R1/r  ->  s = R1/r - 1, 即 r = R1/(1+s)
  花瓣数 = R/r = s。
"""
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge

S = 6  # 花瓣数（六芒星）


def make_seg(b, is_child, sid, parent, length, speed, angle, color, width="0.5"):
    args = [is_child, sid, parent, f"{length:.3f}", f"{speed}", f"{angle:.1f}",
            "1", width, color, "0,0,0", "0", "1.3", "0", "null", "0", "0"]
    st, out = b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)
    assert st == "OK", out
    return out


def disable_body(b, call_out):
    iid = call_out.split("id=")[1].rstrip(")")
    st, o = b.cmd("get", f"obj:{iid}", "lineR")
    line_id = o.strip().split("id=")[1].rstrip(")")
    b.cmd("set", f"obj:{line_id}", "enabled", "false")


def petal_layer(b, base_id, count, r1, phase0, parent_color, child_color):
    """一层花瓣：count 条父（等距）+ 各挂一条子（speed=S, angle=180°）。"""
    r2 = r1 / (1 + S)   # 外摆线滚动圆半径
    for i in range(count):
        ang = phase0 + i * 360.0 / count
        disable_body(b, make_seg(b, 0, base_id + i, "null", r1, 1, ang, parent_color))
        disable_body(b, make_seg(b, 1, base_id + 100 + i, base_id + i, r2, S, 180, child_color))
    return 2 * count


def main():
    b = Bridge()
    print(b.cmd("call", "type:GameManager", "BeginMainGame")[1].strip())
    time.sleep(4)
    print(b.cmd("call", "type:ClickAndDrag", "DeleteAll")[1].strip())
    time.sleep(0.6)

    n = 0
    # 外圆 + 内圆（蓝色边界）
    disable_body(b, make_seg(b, 0, 8000, "null", 5.0, 1, 0, "0.35,0.45,0.90,1")); n += 1
    disable_body(b, make_seg(b, 0, 8001, "null", 1.5, 1, 0, "0.35,0.45,0.90,1")); n += 1

    # 外层六瓣（紫/金）：瓣径 4.57 ~ 3.43
    n += petal_layer(b, 8100, 6, 4.0, 0, "0.62,0.32,0.72,1", "0.95,0.70,0.30,1")
    # 内层六瓣（青/金，相位偏移 30°）：瓣径 2.97 ~ 2.23
    n += petal_layer(b, 8300, 6, 2.6, 30, "0.30,0.80,0.75,1", "0.95,0.70,0.30,1")

    print(f"created {n} segments")
    time.sleep(0.8)

    print(b.cmd("call", "type:ClickAndDrag", "StartOrStop")[1].strip())
    time.sleep(20)

    # 拉远相机，让外圆完整入画
    print(b.cmd("set", "type:CameraPosition", "targetPos", "0,0,-10.5")[1].strip())
    time.sleep(3)
    print(b.cmd("shot", "magic_circle_v5")[1].strip())
    b.close()


if __name__ == "__main__":
    main()

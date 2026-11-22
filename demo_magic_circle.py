"""魔法阵 v2 —— 真正的六芒星（两个三角形链）+ 内外双圆环 + 中心短辐条。

几何：
  等边三角形外接圆半径 R，边长 = sqrt(3)*R ≈ 1.732R。
  链：根线段（中心->顶点A, len=R）-> 子段 A->B（相对转150°）-> B->C（转120°）-> C->A（转120°）闭合。
"""
import math
import time
from client import Bridge

EDGE = 1.7320508  # sqrt(3)


def make_seg(b, is_child, sid, parent, length, speed, angle, color, width="0.35"):
    args = [is_child, sid, parent, f"{length:.3f}", f"{speed}", f"{angle:.1f}",
            "1", width, color, "0,0,0", "0", "1.3", "0", "null", "0", "0"]
    return b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)


def triangle(b, root_id, root_angle, R, color):
    """一个三角形：根 + 3 条弦（首条相对根转 150°，之后各转 120°）。"""
    edge = EDGE * R
    st, out = make_seg(b, 0, root_id, "null", R, 0, root_angle, color)
    assert st == "OK", out
    parent = root_id
    for i, a in enumerate([150, 120, 120]):
        sid = root_id + 1 + i
        st, out = make_seg(b, 1, sid, parent, edge, 0, a, color)
        assert st == "OK", out
        parent = sid


def disable_body(b, call_out):
    """圆环线段的本体是一条从中心到圆周的“半径指针”，会横穿整个图案。

    禁用它的 LineRenderer（TrailRenderer 独立，不受影响），trail 照常画圆。
    call_out: CreateNewSegment 的返回文本，从中解析 instance id。
    """
    iid = call_out.split("id=")[1].rstrip(")")
    st, o = b.cmd("get", f"obj:{iid}", "lineR")
    line_id = o.strip().split("id=")[1].rstrip(")")
    b.cmd("set", f"obj:{line_id}", "enabled", "false")


def main():
    b = Bridge()
    print(b.cmd("call", "type:GameManager", "BeginMainGame")[1].strip())
    time.sleep(4)
    print(b.cmd("call", "type:ClickAndDrag", "DeleteAll")[1].strip())
    time.sleep(0.6)

    n = 0
    # 六芒星：两个三角形（外接圆 R=3.4），紫色 + 金色
    triangle(b, 9000, 0, 3.4, "0.55,0.32,0.72,1");  n += 4
    triangle(b, 9100, 60, 3.4, "1.0,0.78,0.42,1");  n += 4

    # 中心短辐条（内圆内的装饰，洋红）
    for i in range(6):
        st, out = make_seg(b, 0, 9300 + i, "null", 0.9, 0, i * 60 + 30, "0.82,0.3,0.6,1")
        assert st == "OK", out
        n += 1

    # 双圆环（旋转线段，speed=1 转出圆）：外圆蓝、内圆青
    st, out = make_seg(b, 0, 9400, "null", 5.0, 1, 0, "0.32,0.45,0.85,1", "0.45")
    assert st == "OK", out
    disable_body(b, out)
    st, out = make_seg(b, 0, 9401, "null", 1.7, 1, 0, "0.3,0.85,0.8,1", "0.45")
    assert st == "OK", out
    disable_body(b, out)
    n += 2

    print(f"created {n} segments")
    time.sleep(0.8)

    # 播放：StartOrStop -> 所有线段 BeginSequencing，圆环线段转出圆
    print(b.cmd("call", "type:ClickAndDrag", "StartOrStop")[1].strip())

    # speed=1 -> 每秒约 70°，外圆一圈约 5.2s；等两圈保险
    time.sleep(11)
    print(b.cmd("shot", "magic_circle_v2")[1].strip())
    b.close()


if __name__ == "__main__":
    main()

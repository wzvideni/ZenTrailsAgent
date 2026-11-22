"""魔法阵 v3 —— 纯旋转生成的动态对称图案（Zen Trails 正确玩法）。

结构：外圆 + 内圆 + 6 重对称旋轮线（6 父 + 6 子）。
所有线段 speed>0，播放时旋转，端点 trail 叠加成对称花纹；本体 LineRenderer 全隐藏。
"""
import time
from client import Bridge


def make_seg(b, is_child, sid, parent, length, speed, angle, color, width="0.5"):
    args = [is_child, sid, parent, f"{length:.2f}", f"{speed}", f"{angle:.1f}",
            "1", width, color, "0,0,0", "0", "1.3", "0", "null", "0", "0"]
    st, out = b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)
    assert st == "OK", out
    return out  # 返回 out 文本（含 "id=..."），供 disable_body 解析


def disable_body(b, call_out):
    """禁用线段本体（半径指针），只留 TrailRenderer 画轨迹。"""
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
    # 外圆 + 内圆
    out = make_seg(b, 0, 8000, "null", 5.0, 1, 0, "0.40,0.50,0.90,1");  disable_body(b, out); n += 1
    out = make_seg(b, 0, 8001, "null", 2.0, 1, 0, "0.40,0.50,0.90,1");  disable_body(b, out); n += 1

    # 6 重对称旋轮线：父线段（等距同速）+ 子线段（相对父转，形成花瓣）
    for i in range(6):
        ang = i * 60
        out = make_seg(b, 0, 8100 + i, "null", 3.4, 1, ang, "0.62,0.32,0.72,1");  disable_body(b, out); n += 1
        out = make_seg(b, 1, 8200 + i, 8100 + i, 1.4, 1, 0, "0.95,0.70,0.30,1");  disable_body(b, out); n += 1

    print(f"created {n} segments")
    time.sleep(0.8)

    # 播放：所有线段开始旋转，trail 累积成对称花纹
    print(b.cmd("call", "type:ClickAndDrag", "StartOrStop")[1].strip())
    time.sleep(22)
    print(b.cmd("shot", "magic_circle_v3")[1].strip())
    b.close()


if __name__ == "__main__":
    main()

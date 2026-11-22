"""魔法阵 (magic circle) demo —— 对称放射 + 多层六芒星结构，走游戏自身 API。"""
import time
from client import Bridge


def seg(b, sid, length, angle, color):
    """Create one root segment. (isChild,ID,parentID,length,speed,angle,drawTrail,trailWidth,color,pos,layerOrder,glow,isGradient,gradient,centerCam,openInfoP)"""
    args = [0, sid, "null", f"{length:.2f}", "0", f"{angle:.1f}",
            "1", "0.35", color, "0,0,0", "0", "1.3", "0", "null", "0", "0"]
    return b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)


def main():
    b = Bridge()
    print(b.cmd("call", "type:GameManager", "BeginMainGame")[1].strip())
    time.sleep(4)

    print(b.cmd("call", "type:ClickAndDrag", "DeleteAll")[1].strip())
    time.sleep(0.6)

    n = 0
    # 外层 12 芒星（紫色放射骨架）
    for i in range(12):
        st, out = seg(b, 7000 + i, 5.0, i * 30, "0.55,0.32,0.72,1")
        if st != "OK":
            print("fail", out); break
        n += 1
        time.sleep(0.06)

    # 中层六芒星（金色，正六边形顶点）
    for i in range(6):
        st, out = seg(b, 7100 + i, 3.4, i * 60, "1.0,0.78,0.42,1")
        if st != "OK":
            print("fail", out); break
        n += 1
        time.sleep(0.06)

    # 中层六芒星（蓝色，旋转 30° 叠加成 12 芒）
    for i in range(6):
        st, out = seg(b, 7200 + i, 3.4, i * 60 + 30, "0.32,0.45,0.85,1")
        if st != "OK":
            print("fail", out); break
        n += 1
        time.sleep(0.06)

    # 内层六芒星（洋红，旋转 15°）
    for i in range(6):
        st, out = seg(b, 7300 + i, 1.7, i * 60 + 15, "0.82,0.3,0.6,1")
        if st != "OK":
            print("fail", out); break
        n += 1
        time.sleep(0.06)

    print(f"created {n} segments")
    time.sleep(1.2)
    print(b.cmd("shot", "magic_circle")[1].strip())
    b.close()


if __name__ == "__main__":
    main()

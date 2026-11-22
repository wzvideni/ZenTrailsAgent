"""天衍神圣共鸣·万象生命之花复合大魔法阵
Celestial Multi-Matrix Magic Circle (Masterpiece Edition)

融合特性：
1. 【中枢真灵·生命之花圣轮 (Central Flower of Life Rosette)】：
   - 传承自 flower_of_life_rosette.py 的谐振逆旋美学：12 组扇骨以 +1.0 速与 -2.0 速逆向交织
   - 太阳金与瑰丽洋红双色交错，在中央殿堂盛放 12 瓣重叠神圣几何莲华
2. 【六极环卫·多元星位天体从阵群 (Six Satellite Sub-Magic Circles in Two Styles)】：
   - 在 R=3.60 的周天六合星位（0°, 60°, 120°, 180°, 240°, 300°）建立独立运行的卫星子法阵群
   - 样式一【天阳三曜真灵阵 (Solar Triquetra Rosette)】（0°, 120°, 240°）：
     三芒太阳真金结界环 + 3瓣高能火精生命之花逆旋纹 + 白金核心
   - 样式二【苍穹四象星芒阵 (Astral Quad-Star Octagram)】（60°, 180°, 300°）：
     极光碧蓝外环 + 4角星芒菱晶灵纹 + 秘术紫晶同心内印
3. 【贯通周天·天轨神链与同心统御环 (Connecting Orbital Leys & Enclosure)】：
   - R=3.60 环绕贯通全部六大卫星阵核心的黄金天轨
   - R=2.70 与 R=2.10 中阶神圣紫晶双环隔离结界
4. 【最外天界禁咒之垣 (Outermost 24-Cusp Solar Corona & Double Boundary)】：
   - R=4.65 / 4.80 极光碧蓝与天界真金双重封印天堑
   - 24 芒日轮神圣耀斑外冠（R=5.20），向外喷薄 24 道璀璨纯阳尖芒
   - R=5.25 最外层极光金晕天轨收束
"""
import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge


def seg(b, is_child, sid, parent_id, length, speed, angle,
        color, width="0.40", glow="1.8", draw_trail="1"):
    """创建线段并隐藏机械臂实体，仅留纯净流光轨迹。"""
    parent_str = str(parent_id) if parent_id is not None and parent_id != "null" else "null"
    args = [
        "1" if is_child else "0",
        str(sid),
        parent_str,
        f"{length:.4f}",
        f"{speed}",
        f"{angle:.2f}",
        str(draw_trail),
        str(width),
        str(color),
        "0,0,0",
        "0",
        str(glow),
        "0",
        "null",
        "0",
        "0"
    ]
    st, out = b.cmd("call", "type:ClickAndDrag", "CreateNewSegment", *args)
    b.cmd("set", f"path:/ClickAndDragMaster/Segment(Clone)", "hideMesh", "true")
    return st, out


def setup_dark_mode(b):
    try:
        st, out = b.cmd("find", "Background")
        if st == "OK" and len(out.splitlines()) > 1:
            oid = out.splitlines()[1].split()[1]
            st, out = b.cmd("get", f"obj:{oid}", "currentBG")
            if "id=" in out:
                bg_id = out.strip().split("id=")[1].rstrip(")")
                b.cmd("call", f"obj:{bg_id}", "SetActive", "false")
        st, out = b.cmd("find", "Camera")
        if st == "OK" and len(out.splitlines()) > 1:
            cam = out.splitlines()[1].split()[1]
            b.cmd("set", f"obj:{cam}", "backgroundColor", "0.02,0.02,0.04,1")
            b.cmd("set", f"obj:{cam}", "clearFlags", "SolidColor")
    except Exception as e:
        print(f"dark mode note: {e}")


def build_celestial_multi_matrix(b):
    print("1. 初始化场景...")
    b.cmd("set", "type:ClickAndDrag", "paused", "false")
    b.cmd("call", "type:GameManager", "BeginMainGame")
    time.sleep(1.2)
    b.cmd("call", "type:ClickAndDrag", "DeleteAll")
    time.sleep(0.4)

    setup_dark_mode(b)
    # 视野调整适配 R=5.25 的庞大法阵群
    b.cmd("set", "type:CameraPosition", "targetPos", "0,0,-12.8")

    # =========================================================================
    # 色彩预设
    # =========================================================================
    C_GOLD = "1.00,0.85,0.28,1"       # 太阳真金
    C_ROSE = "1.00,0.25,0.58,1"       # 神圣玫瑰紫红
    C_CYAN = "0.20,0.92,1.00,1"       # 极光苍穹碧蓝
    C_VIOLET = "0.78,0.32,1.00,1"     # 秘术虚空紫晶
    C_AMBER = "1.00,0.60,0.15,1"      # 炽阳琥珀火金
    C_WHITE_GOLD = "1.00,0.98,0.85,1" # 极光白金核
    C_AQUA = "0.25,1.00,0.85,1"       # 灵能碧翠

    sid = 1000

    print("2. 构建【中枢圣所：十二瓣生命之花圣轮 (Flower of Life Rosette)】...")
    # 核心超亮白金环
    seg(b, False, sid, "null", 0.52, 2.0, 0.0, C_WHITE_GOLD, width="0.48", glow="2.2")
    sid += 1

    # 12 根生命之花扇骨逆旋组 (传承自 flower_of_life_rosette.py 的 1 : -2 逆旋谐振)
    for i in range(12):
        ang = i * 30.0
        pid = sid
        cid = sid + 1
        sid += 2
        col = C_GOLD if (i % 2 == 0) else C_ROSE
        # 扇骨载体 (长 1.35, 速 1.0, 不画线，中间星位)
        seg(b, False, pid, "null", 1.35, 1.0, ang, "0,0,0,0", draw_trail="0")
        # 扇梢流光臂 (长 1.05, 速 -2.0, 描绘 12 瓣神圣交织生命之花)
        seg(b, True, cid, pid, 1.05, -2.0, 0.0, col, width="0.38", glow="1.85")

    # 中枢隔离双重同心阵环
    seg(b, False, sid, "null", 2.05, 1.0, 0.0, C_CYAN, width="0.40", glow="1.7")
    sid += 1
    seg(b, False, sid, "null", 2.22, -1.0, 15.0, C_VIOLET, width="0.35", glow="1.6")
    sid += 1

    print("3. 构建【六极周天贯通天轨与内共鸣环】...")
    # 贯穿六大从阵中枢的黄金天轨
    seg(b, False, sid, "null", 3.60, 1.0, 0.0, C_GOLD, width="0.42", glow="1.8")
    sid += 1
    # 内部交感环
    seg(b, False, sid, "null", 2.70, -1.0, 30.0, C_VIOLET, width="0.36", glow="1.6")
    sid += 1

    print("4. 构建【六极环卫卫星法阵群：两种不同样式魔法阵】...")
    # 六个天体基座星位 (0°, 60°, 120°, 180°, 240°, 300°)
    satellite_angles = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]

    for idx, sat_ang in enumerate(satellite_angles):
        # 载体臂 (从中心延伸至 R=3.60，speed=0 静态定位，不画轨迹)
        anchor_id = sid
        sid += 1
        seg(b, False, anchor_id, "null", 3.60, 0.0, sat_ang, "0,0,0,0", draw_trail="0")

        if idx % 2 == 0:
            # =================================================================
            # 样式一：【天阳三曜真灵阵 (Solar Triquetra Rosette)】(0°, 120°, 240°)
            # =================================================================
            # 1. 卫星法阵外环
            seg(b, True, sid, anchor_id, 0.88, 2.0, 0.0, C_AMBER, width="0.35", glow="1.8")
            sid += 1
            # 2. 内部三瓣生命之花 (3 骨扇组，速比 3 : -6)
            for j in range(3):
                tri_ang = j * 120.0
                pid = sid
                cid = sid + 1
                sid += 2
                seg(b, True, pid, anchor_id, 0.44, 3.0, tri_ang, "0,0,0,0", draw_trail="0")
                seg(b, True, cid, pid, 0.44, -6.0, 0.0, C_GOLD, width="0.34", glow="1.9")
            # 3. 核心火精微核
            seg(b, True, sid, anchor_id, 0.16, 4.0, 0.0, C_WHITE_GOLD, width="0.42", glow="2.2")
            sid += 1
        else:
            # =================================================================
            # 样式二：【苍穹四象星芒阵 (Astral Quad-Star Octagram)】(60°, 180°, 300°)
            # =================================================================
            # 1. 卫星法阵外环
            seg(b, True, sid, anchor_id, 0.88, -2.0, 0.0, C_CYAN, width="0.35", glow="1.8")
            sid += 1
            # 2. 内部四角星芒灵纹 (4 骨扇组，速比 2 : -6，生成尖锐四芒星轮)
            for j in range(4):
                quad_ang = j * 90.0
                pid = sid
                cid = sid + 1
                sid += 2
                seg(b, True, pid, anchor_id, 0.44, 2.0, quad_ang, "0,0,0,0", draw_trail="0")
                seg(b, True, cid, pid, 0.44, -6.0, 0.0, C_AQUA, width="0.34", glow="1.9")
            # 3. 内部紫晶微环与星核
            seg(b, True, sid, anchor_id, 0.40, 3.0, 45.0, C_VIOLET, width="0.28", glow="1.6")
            sid += 1
            seg(b, True, sid, anchor_id, 0.16, -4.0, 0.0, C_CYAN, width="0.42", glow="2.2")
            sid += 1

    print("5. 构建【最外天界禁咒之垣与 24 芒太阳耀斑光冠】...")
    # 封印双环
    seg(b, False, sid, "null", 4.65, 1.0, 0.0, C_CYAN, width="0.42", glow="1.7")
    sid += 1
    seg(b, False, sid, "null", 4.82, -1.0, 7.5, C_GOLD, width="0.45", glow="1.8")
    sid += 1

    # 24 芒日轮神圣耀斑外冠 (1.0 速与 -23.0 逆向谐振生成 24 道外向喷薄金焰)
    for k in range(24):
        ang = k * 15.0
        pid = sid
        cid = sid + 1
        sid += 2
        seg(b, False, pid, "null", 4.75, 1.0, ang, "0,0,0,0", draw_trail="0")
        seg(b, True, cid, pid, 0.45, -23.0, 0.0, C_GOLD, width="0.32", glow="1.9")

    # 最外天界金晕光环
    seg(b, False, sid, "null", 5.25, 0.5, 0.0, C_GOLD, width="0.36", glow="1.6")
    sid += 1

    st, total_segs = b.cmd("get", "type:ClickAndDrag", "segments.Count")
    print(f"法阵构建完成，共计激活线段节点: {total_segs.strip()}")


def run_and_capture(b):
    print("6. 启动运转并绘制多重神圣法阵流光...")
    b.cmd("set", "type:SettingsPanel", "hideSegments", "true")
    b.cmd("call", "type:ClickAndDrag", "StartOrStop")

    print("流光律动绘制中（运转 22 秒让所有主阵、卫星阵与外日轮完全闭合）...")
    time.sleep(22.0)

    print("定格完满状态...")
    b.cmd("call", "type:ClickAndDrag", "TogglePause")
    time.sleep(1.0)

    # 保存存档为官方 .mndla
    print("保存为官方存档 CelestialMultiMatrix.mndla...")
    b.cmd("call", "type:SaveAndLoadManager", "Save", "CelestialMultiMatrix", "custom")
    time.sleep(0.5)

    # 截图
    print("截取 1080P 高清神圣法阵壁纸...")
    st, path = b.cmd("shot", "celestial_multi_matrix_masterpiece")
    print(f"高清截图保存至: {path.strip()}")
    return path.strip()


def main():
    b = Bridge()
    try:
        build_celestial_multi_matrix(b)
        shot_path = run_and_capture(b)
    finally:
        b.close()


if __name__ == "__main__":
    main()

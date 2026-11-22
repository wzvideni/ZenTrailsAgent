"""天体禁咒·终焉十二芒星与群星宿命法阵 (Grand Astral Magic Circle - Masterpiece Edition)

十二重宏大几何与神圣色彩体系：
1. 最外天轨金界双环 (R=5.60, 5.40) - 极光苍蓝与灵能紫晶
2. 24芒外环太阳耀斑光冠 (R=5.12, S=24) - 辉煌太阳真金
3. 第一重隔离符文环 (R=4.90) - 水天极光碧蓝
4. 六座外环星轨律动阵 (R=4.30, S=6) - 宇宙洋红与冰晶天青交织的起伏星带
5. 第二重隔离符文双环 (R=3.85, 3.65) - 深邃紫罗兰与苍穹碧蓝
6. 双重交错十二芒星圣辉 (R=3.20, S=6, 0°太阳金 + 30°秘术翠青) - 宏伟交错12芒星瓣
7. 中阶封印紫晶结界环 (R=2.65) - 幻紫圣印
8. 十二瓣内层神圣曼陀罗莲华 (R=2.15, S=12) - 绯红玫瑰莲华结界
9. 内殿结界双环 (R=1.90, 1.75) - 碧水与烈阳双色同心环
10. 八芒秘法星芒结界 (R=1.40, S=8) - 翡翠灵能八角星
11. 圣所核心双环 (R=1.15, 0.95) - 幽紫与极光白蓝
12. 极光奇点·万华之眼 (R=0.60, 0.28) - 超高亮白金耀核与万华神辉

自动化特性：
- 自动解除暂停锁定，确保流光完全旋转绘制
- 自动隐藏物理机械臂，保持流光法阵纯净无暇
- 截图前自动隐藏 Canvas UI（无按钮、无提示），生成纯净 1080P 壁纸级画面
- 自动保存为游戏官方 .mndla 存档文件
"""
import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from client import Bridge


def make_segment(b, is_child, sid, parent_id, length, speed, angle,
                 color, width="0.40", glow="1.6", draw_trail="1"):
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
    if st != "OK":
        print(f"Error creating segment {sid}: {out}")
        return None
    
    try:
        iid = out.split("id=")[1].rstrip(")")
        st_l, out_l = b.cmd("get", f"obj:{iid}", "lineR")
        if "id=" in out_l:
            line_id = out_l.strip().split("id=")[1].rstrip(")")
            b.cmd("set", f"obj:{line_id}", "enabled", "false")
        st_d, out_d = b.cmd("get", f"obj:{iid}", "dotRend")
        if "id=" in out_d:
            dot_id = out_d.strip().split("id=")[1].rstrip(")")
            b.cmd("set", f"obj:{dot_id}", "enabled", "false")
    except Exception as e:
        pass
    
    return out


def setup_dark_mode(b):
    """设置深邃暗夜星空背景。"""
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
            b.cmd("set", f"obj:{cam}", "backgroundColor", "0.02,0.02,0.05,1")
            b.cmd("set", f"obj:{cam}", "clearFlags", "SolidColor")
    except Exception as e:
        print(f"dark mode note: {e}")


def build_grand_magic_circle(b):
    print("Initializing environment...")
    # 确保解除暂停状态
    b.cmd("set", "type:ClickAndDrag", "paused", "false")
    b.cmd("call", "type:GameManager", "BeginMainGame")
    time.sleep(2.0)
    b.cmd("call", "type:ClickAndDrag", "DeleteAll")
    time.sleep(0.6)
    
    setup_dark_mode(b)
    
    # 相机居中且精准适配半径 5.60 的外环 (z = -12.8)
    b.cmd("set", "type:CameraPosition", "targetPos", "0,0,-12.8")
    
    sid = 10000
    seg_count = 0
    
    print("Generating Layer 1: Outermost Divine Boundary Rings...")
    # 1A. 最外边界环 R=5.60 (极光苍蓝)
    make_segment(b, False, sid, None, 5.60, 1, 0, "0.15,0.92,1.00,1", width="0.44", glow="1.8")
    sid += 1; seg_count += 1
    # 1B. 次外边界环 R=5.40 (灵能紫晶)
    make_segment(b, False, sid, None, 5.40, 1, 0, "0.80,0.30,1.00,1", width="0.32", glow="1.6")
    sid += 1; seg_count += 1

    print("Generating Layer 2: 24-Cusp Solar Corona (S=24)...")
    # 2. 24芒外环太阳耀斑光冠 (灿烂太阳真金)
    r1_corona = 5.12
    r2_corona = r1_corona / 25.0
    for i in range(4):
        ang = i * 90.0
        pid = sid
        make_segment(b, False, pid, None, r1_corona, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_corona, 24, 180.0, "1.00,0.85,0.25,1", width="0.34", glow="1.7")
        sid += 1; seg_count += 2

    print("Generating Layer 3: Containment Ring 1 (R=4.90)...")
    # 3. 第一重隔离符文环 (水天极光碧蓝)
    make_segment(b, False, sid, None, 4.90, 1, 0, "0.20,0.95,0.95,1", width="0.36", glow="1.6")
    sid += 1; seg_count += 1

    print("Generating Layer 4: 6 Orbiting Celestial Seal Ribbons (R=4.30, S=6)...")
    # 4. 六座外环星轨律动阵 (洋红玫瑰与极光天青交错起伏的星轨缎带)
    for i in range(6):
        ang = i * 60.0
        pid = sid
        make_segment(b, False, pid, None, 4.30, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        mid = sid
        make_segment(b, True, mid, pid, 0.40, 6, 180.0, "1.00,0.35,0.80,1", width="0.38", glow="1.7")
        sid += 1
        make_segment(b, True, sid, mid, 0.22, -6, 0.0, "0.25,0.95,1.00,1", width="0.32", glow="1.6")
        sid += 1; seg_count += 3

    print("Generating Layer 5: Containment Rings 2 (R=3.85, 3.65)...")
    # 5. 第二重隔离双环 (深邃紫罗兰与苍穹碧蓝)
    make_segment(b, False, sid, None, 3.85, 1, 0, "0.75,0.25,1.00,1", width="0.35", glow="1.6")
    sid += 1; seg_count += 1
    make_segment(b, False, sid, None, 3.65, 1, 0, "0.20,0.85,1.00,1", width="0.28", glow="1.5")
    sid += 1; seg_count += 1

    print("Generating Layer 6: Dual Interlaced Dodecagram & Hexagram...")
    # 6A. 炽烈黄金主六芒星 (0°, 60°, 120°, 180°, 240°, 300°)
    r1_star = 3.20
    r2_star = r1_star / 7.0
    for i in range(6):
        ang = i * 60.0
        pid = sid
        make_segment(b, False, pid, None, r1_star, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_star, 6, 180.0, "1.00,0.85,0.20,1", width="0.46", glow="1.9")
        sid += 1; seg_count += 2

    # 6B. 交错秘术天青六芒星 (相位偏移 30°: 30°, 90°, 150°, 210°, 270°, 330°)
    for i in range(6):
        ang = 30.0 + i * 60.0
        pid = sid
        make_segment(b, False, pid, None, r1_star, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_star, 6, 180.0, "0.20,0.95,0.90,1", width="0.44", glow="1.8")
        sid += 1; seg_count += 2

    print("Generating Layer 7: Intermediate Containment Ring (R=2.65)...")
    # 7. 中阶封印环 (紫晶圣印)
    make_segment(b, False, sid, None, 2.65, 1, 0, "0.85,0.35,1.00,1", width="0.36", glow="1.6")
    sid += 1; seg_count += 1

    print("Generating Layer 8: 12-Petal Sacred Lotus Mandala (S=12)...")
    # 8. 十二瓣内层曼陀罗莲华 (深绯瑰丽莲华)
    r1_lotus = 2.15
    r2_lotus = r1_lotus / 13.0
    for i in range(6):
        ang = i * 60.0
        pid = sid
        make_segment(b, False, pid, None, r1_lotus, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_lotus, 12, 180.0, "1.00,0.40,0.75,1", width="0.36", glow="1.7")
        sid += 1; seg_count += 2

    print("Generating Layer 9: Inner Sanctum Rings (R=1.90, 1.75)...")
    # 9. 内殿结界双环 (碧水与烈阳)
    make_segment(b, False, sid, None, 1.90, 1, 0, "0.25,0.90,1.00,1", width="0.35", glow="1.6")
    sid += 1; seg_count += 1
    make_segment(b, False, sid, None, 1.75, 1, 0, "1.00,0.85,0.30,1", width="0.28", glow="1.5")
    sid += 1; seg_count += 1

    print("Generating Layer 10: 8-Cusped Mystic Star (S=8)...")
    # 10. 八芒翡翠星芒
    r1_octa = 1.40
    r2_octa = r1_octa / 9.0
    for i in range(4):
        ang = i * 90.0
        pid = sid
        make_segment(b, False, pid, None, r1_octa, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_octa, 8, 180.0, "0.30,1.00,0.65,1", width="0.40", glow="1.8")
        sid += 1; seg_count += 2

    print("Generating Layer 11: Core Boundary Rings (R=1.15, 0.95)...")
    # 11. 核心秘境双环 (幽紫与幻青)
    make_segment(b, False, sid, None, 1.15, 1, 0, "0.85,0.30,1.00,1", width="0.35", glow="1.6")
    sid += 1; seg_count += 1
    make_segment(b, False, sid, None, 0.95, 1, 0, "0.20,0.92,1.00,1", width="0.28", glow="1.5")
    sid += 1; seg_count += 1

    print("Generating Layer 12: Arcane Singularity Core...")
    # 12A. 核心六芒白金耀核
    r1_core = 0.60
    r2_core = r1_core / 7.0
    for i in range(3):
        ang = i * 120.0
        pid = sid
        make_segment(b, False, pid, None, r1_core, 1, ang, "0,0,0,0", draw_trail="0")
        sid += 1
        make_segment(b, True, sid, pid, r2_core, 6, 180.0, "1.00,0.98,0.70,1", width="0.45", glow="2.0")
        sid += 1; seg_count += 2

    # 12B. 中心永恒源核 (极光白蓝奇点)
    make_segment(b, False, sid, None, 0.28, 1, 0, "0.92,0.98,1.00,1", width="0.55", glow="2.2")
    sid += 1; seg_count += 1

    print(f"Successfully constructed {seg_count} segments across 12 layers!")
    return seg_count


def run_and_capture(b):
    print("Setting hideSegments in SettingsPanel...")
    b.cmd("set", "type:SettingsPanel", "hideSegments", "true")
    time.sleep(0.3)

    print("Starting simulation to cast the Grand Magic Circle...")
    b.cmd("call", "type:ClickAndDrag", "StartOrStop")
    
    # 运行24秒，让所有流光轨迹在宇宙中完整绘制闭合
    print("Drawing celestial trails across the cosmos (24 seconds)...")
    time.sleep(24.0)
    
    # 暂停保持当前完美法阵
    print("Pausing simulation with TogglePause to freeze the magic circle in pristine glory...")
    b.cmd("call", "type:ClickAndDrag", "TogglePause")
    time.sleep(1.0)
    
    # 保存为官方 .mndla 存档文件
    print("Saving to preset/custom .mndla save file...")
    b.cmd("call", "type:SaveAndLoadManager", "Save", "GrandAstralCircle", "custom")
    time.sleep(0.5)

    # 截图前隐藏整个 UI Canvas，拍摄无任何按钮遮挡的纯净壁纸级画面
    print("Hiding UI Canvas for pristine capture...")
    b.cmd("set", "path:/Canvas", "enabled", "false")
    time.sleep(0.5)

    print("Capturing 1080p high-resolution masterpiece screenshot...")
    st, path = b.cmd("shot", "grand_magic_circle_masterpiece")
    print(f"Screenshot saved: {path.strip()}")

    # 恢复 UI Canvas
    b.cmd("set", "path:/Canvas", "enabled", "true")

    return path.strip()


def main():
    b = Bridge()
    try:
        build_grand_magic_circle(b)
        shot_path = run_and_capture(b)
    finally:
        b.close()


if __name__ == "__main__":
    main()

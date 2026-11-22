"""恢复并完美重现「折扇点位与金华之轮 (Fan & Flower of Life Rosette)」

特点：
1. 初始状态：6 根扇骨沿 0°, 30°, 60°, 90°, 120°, 150° 放射排布，
   在内径 R=2.15 与外径 R=3.80 处形成两圈优美对称的璀璨星光点位，宛如一把展开的东方折扇。
2. 运转状态：子臂以 -2 倍速逆向谐振，每个点位各自划出一条倾角递增的金光椭圆，
   最终完美交织为神圣几何学中的「生命之花 / 金华十二芒星轮 (Flower of Life Rosette)」。
3. 自动生成两张高清图：
   - 扇形骨架与星光点位图 (fan_skeleton.png)
   - 运转闭合后的完整生命之花金辉图 (fan_rosette_drawn.png)
4. 自动保存为游戏官方存档 FanRosette.mndla
"""
import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from zentrails_agent.client import Bridge


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
            b.cmd("set", f"obj:{cam}", "backgroundColor", "0.02,0.02,0.05,1")
            b.cmd("set", f"obj:{cam}", "clearFlags", "SolidColor")
    except Exception as e:
        print(f"dark mode note: {e}")


def main():
    b = Bridge()
    print("1. 初始化场景...")
    b.cmd("set", "type:ClickAndDrag", "paused", "false")
    b.cmd("call", "type:GameManager", "BeginMainGame")
    time.sleep(1.5)
    b.cmd("call", "type:ClickAndDrag", "DeleteAll")
    time.sleep(0.5)

    setup_dark_mode(b)
    # 相机居中适配 R=3.80 的扇面
    b.cmd("set", "type:CameraPosition", "targetPos", "0,0,-10.5")

    print("2. 构建 6 骨扇形骨架与点位 (0° ~ 150°)...")
    for i in range(6):
        ang = i * 30.0
        pid = 5000 + i
        cid = 6000 + i
        # 根部扇骨 (长 2.15, 速 1, 不画线，中间端点形成内层星位)
        b.cmd("call", "type:ClickAndDrag", "CreateNewSegment",
              "0", str(pid), "null", "2.15", "1", str(ang),
              "0", "0.3", "0,0,0,0", "0,0,0", "0", "1.2", "0", "null", "0", "0")
        # 扇梢子臂 (长 1.65, 速 -2, 画金色辉光轨迹，外层端点形成外弧星位)
        b.cmd("call", "type:ClickAndDrag", "CreateNewSegment",
              "1", str(cid), str(pid), "1.65", "-2", "0",
              "1", "0.40", "1.00,0.85,0.28,1", "0,0,0", "0", "1.8", "0", "null", "0", "0")

    time.sleep(0.8)
    
    # 状态 A：截取扇子点位初始形态（无 UI 遮挡）
    print("3. 捕获【扇形点位骨架状态】截图...")
    b.cmd("set", "path:/Canvas", "enabled", "false")
    time.sleep(0.4)
    b.cmd("shot", "fan_skeleton")
    b.cmd("set", "path:/Canvas", "enabled", "true")
    time.sleep(0.3)

    # 状态 B：启动运转绘制生命之花金华圣轮
    print("4. 启动运转并隐藏物理骨架，绘制生命之花金华星轮...")
    b.cmd("set", "type:SettingsPanel", "hideSegments", "true")
    b.cmd("call", "type:ClickAndDrag", "StartOrStop")
    
    # 运行绘制
    print("正在运转绘制流光轨迹 (18 秒)...")
    time.sleep(18.0)

    # 截取最终运转完成的流光大图（在保存存档前截，避免触发 reset）
    print("5. 捕获【生命之花金华星轮】截图...")
    b.cmd("set", "path:/Canvas", "enabled", "false")
    time.sleep(0.4)
    st, path = b.cmd("shot", "fan_rosette_complete")
    b.cmd("set", "path:/Canvas", "enabled", "true")

    # 暂停定格并保存存档
    print("定格完好形态并保存官方存档...")
    b.cmd("call", "type:ClickAndDrag", "TogglePause")
    time.sleep(0.5)
    b.cmd("call", "type:SaveAndLoadManager", "Save", "FanRosette", "custom")
    time.sleep(0.5)

    print(f"全部完成！截图保存在: {path.strip()}")
    b.close()


if __name__ == "__main__":
    main()

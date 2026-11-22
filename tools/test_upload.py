"""zen_upload 回归测试：验证「先打开 Uploader 面板」的修复。

背景：
    zen_upload 旧实现直接调用 TakeScreenshot() + Upload()，没有先 Open() 面板。
    ieTakeScreenshot 协程结束时会把 Uploader/SettingsPanel/InspPanel 的
    localScale 硬设回 (1,1,1) 却绕过 OpenWithCurtain 状态机，导致面板
    scale=1（全屏黑框）但 sOpener.open=false；上传成功后关闭逻辑
    if(open){Close()} 判定失败，黑框永久卡住无法关闭。

    zen_upload 现已在 Upload 前先调用 Uploader.Open() 建立 open=true 状态，
    使上传成功后的自动关闭逻辑正常生效。

用法（仓库根目录执行）：
    uv run python tools/test_upload.py              # 完整流程 + 等待面板自动收起
    uv run python tools/test_upload.py --skip-upload  # 只验证 Open/Close 状态机，不真上传
    uv run python tools/test_upload.py --title "测试图案"   # 自定义标题

注意：真实上传有 30 秒冷却，且会公开发布到 Steam 创意工坊。
"""
import argparse
import sys
import time

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
import mcp_server  # noqa: E402  (复用 handle_call 走与 MCP 客户端完全相同的路径)


def call(name, args):
    r = mcp_server.handle_call(name, args)
    if isinstance(r, dict) and "content" in r:
        return "\n".join(c.get("text", "") for c in r["content"])
    return str(r)


def bridge(cmd, *args):
    """直接读桥状态，用于断言面板是否收起的底层真值。"""
    st, out = mcp_server.conn.call(cmd, *args)
    return st, out


def uploader_scale_x():
    """面板 scale 的 x 分量（0=收起，1=撑开/黑框）。"""
    st, out = bridge("get", "type:Uploader", "transform.localScale")
    # 输出形如 "transform = Uploader(id=37080)\nlocalScale = (0.0, 1.0, 1.0)"
    try:
        return float(out.split("localScale = (")[1].split(",")[0])
    except Exception:
        return None


def uploader_open():
    st, out = bridge("get", "type:Uploader", "sOpener.open")
    return out.strip()


def game_state():
    st, out = bridge("get", "type:GameManager", "gameState")
    return out.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="旋转花瓣")
    ap.add_argument("--skip-upload", action="store_true",
                    help="只验证 Open/Close 状态机，不发真实上传")
    args = ap.parse_args()

    print("== 前置状态 ==")
    print("gameState      :", game_state())
    print("Uploader scale.x:", uploader_scale_x())
    print("Uploader open  :", uploader_open())
    sx = uploader_scale_x()
    if sx is not None and sx > 0.5 and not uploader_open().endswith("True"):
        raise SystemExit("前置状态异常：面板已撑开但 open=false（黑框已卡住）")

    if args.skip_upload:
        print("\n== 状态机验证（不真上传）==")
        print("Open  :", call("zen_call", {"selector": "type:Uploader", "method": "Open"}))
        time.sleep(0.5)
        print("  scale.x =", uploader_scale_x(), "/ open =", uploader_open())
        assert uploader_open().endswith("True"), "Open() 后 open 应为 True"
        print("Close :", call("zen_call", {"selector": "type:Uploader", "method": "Close"}))
        time.sleep(1.0)
        print("  scale.x =", uploader_scale_x(), "/ open =", uploader_open())
        sx = uploader_scale_x()
        assert sx is not None and sx < 0.5, "Close() 后 scale.x 应回到 0"
        print("\nPASS: Open/Close 状态机正常，面板能正确收起。")
        return

    print("\n== 加载存档 ==")
    print(call("zen_load", {"name": "旋转花瓣", "type": "custom"}))
    time.sleep(4)

    print("\n== 上传（走 zen_upload 工具）==")
    print(call("zen_upload", {"title": args.title}))
    print("  上传后立即：scale.x =", uploader_scale_x(), "/ open =", uploader_open())

    print("\n== 等待上传完成 + 面板自动收起 ==")
    for i in range(30):  # 最多约 30 秒
        time.sleep(1)
        sx = uploader_scale_x()
        open_ = uploader_open()
        st, status = bridge("get", "type:Uploader", "statusText.text")
        print(f"  t={i + 1}s scale.x={sx} open={open_} status={status.strip()[:40]!r}")
        if sx is not None and sx < 0.5 and not open_.endswith("True"):
            print("\nPASS: 上传后面板自动收起（scale.x=0, open=false），黑框未卡住。")
            print("gameState :", game_state())
            return
    print("\nFAIL: 30 秒内面板未收起（黑框可能卡住）。")
    sys.exit(1)


if __name__ == "__main__":
    main()

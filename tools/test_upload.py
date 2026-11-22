"""完整上传流程测试：加载「旋转花瓣」存档 -> 设标题/描述 -> 截图缩略图 -> 上传 -> 读状态。"""
import time
from client import Bridge


def main():
    b = Bridge()
    print("steamworks:", b.cmd("get", "type:GameManager", "steamworksInitiated")[1].strip())

    # 进入编辑场景
    print("enter:", b.cmd("call", "type:GameManager", "BeginMainGame")[1].strip())
    time.sleep(4)

    # 加载旋转花瓣存档
    print("load:", b.cmd("loadsave", "旋转花瓣", "custom")[1].strip())
    time.sleep(5)
    st, out = b.cmd("get", "type:ClickAndDrag", "segments")
    print("segments:", out.strip()[:120])

    # 设置标题/描述
    st, out = b.cmd("get", "type:Uploader", "designTitle")
    tid = out.split("id=")[1].split(")")[0]
    print("set title:", b.cmd("set", f"obj:{tid}", "text", "旋转花瓣")[1].strip())
    st, out = b.cmd("get", "type:Uploader", "description")
    did = out.split("id=")[1].split(")")[0]
    print("set desc:", b.cmd("set", f"obj:{did}", "text", "AI 测试上传 - 旋转花瓣图案")[1].strip())

    # 截图缩略图
    print("thumbnail:", b.cmd("call", "type:Uploader", "TakeScreenshot")[1].strip())
    time.sleep(1.5)

    # 上传
    print("upload:", b.cmd("call", "type:Uploader", "Upload")[1].strip())
    time.sleep(3)

    # 读状态
    print("status:", b.cmd("get", "type:Uploader", "statusText")[1].strip())
    b.close()


if __name__ == "__main__":
    main()

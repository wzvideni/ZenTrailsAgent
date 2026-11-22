# Zen Trails AI 控制方案（已验证可行）

目标：让 AI Agent（含 DSH）通过 MCP 工具控制《Zen Trails》（Steam，Unity 2019.1 Mono）。

结论：**可行**。AI 已实测通过游戏自己的 API 生成了一条 36 段的嵌套曼陀罗轨迹，并截图存证。

## 架构

```
AI Agent (DSH)
   │  MCP stdio (JSON-RPC 2.0)
   ▼
mcp_server.py  ──(line protocol / TCP 127.0.0.1:5123)──▶  ZenTrailsAgent.dll
                                                            (BepInEx 5 插件，游戏进程内)
                                                               │  Unity 主线程执行
                                                               ▼
                                                            游戏 C# API（反射调用）
```

- 在游戏进程内注入 BepInEx 插件，暴露 TCP 控制面（127.0.0.1:5123）。
- 插件把每个命令放到 Unity 主线程 `Update()` 里执行，安全地调用游戏 C# 方法。
- MCP server 把协议封装成 8 个工具，任何 MCP 客户端都能调用。

## 文件清单

| 文件 | 作用 |
|------|------|
| `src/AgentBridge.cs` | BepInEx 插件源码（C# 5，Framework csc 编译） |
| `dist/ZenTrailsAgent.dll` | 编译产物（`tools/build_plugin.ps1` 生成，已部署到游戏） |
| `client.py` | 桥接客户端（Python，stdio 之外也可直接用） |
| `mcp_server.py` | MCP server（stdio / JSON-RPC 2.0，11 个工具） |
| `tools/build_plugin.ps1` | 编译 + 部署 + 重启游戏 |
| `tools/test_tools.py` / `tools/test_clickui.py` | MCP 工具端到端测试 |
| `demo_draw.py` / `demo_mandala.py` | 演示脚本 |
| `tools/Dump.cs` / `tools/DumpIL.cs` | 反射/IL 反编译工具源码（Cecil） |

## MCP 工具

| 工具 | 说明 |
|------|------|
| `zen_cmd` | 通用桥命令（ping/types/describe/scene/find/get/set/call/coroutine/shot/mouse/drag/clickui/focus/log） |
| `zen_screenshot` | 截图到 `<游戏目录>\shots\*.png`；`return_image=true` 时内联返回缩放后的 JPEG（供 vision 模型直接看） |
| `zen_scene` | 转储场景层级 |
| `zen_find` | 按类型列出活动实例（带 instance ID 和路径） |
| `zen_types` | 枚举游戏类型（可过滤子串） |
| `zen_describe` | 反射类型（字段/属性/方法/枚举） |
| `zen_get` | 读字段/属性（点路径，静态/实例均可） |
| `zen_set` | 写字段/属性（按声明类型转换，静态/实例均可） |
| `zen_call` | 调用普通方法（按参数类型转换） |
| `zen_coroutine` | 调用协程方法（`IEnumerator`），经 `StartCoroutine` 真正执行 |
| `zen_clickui` | 进程内点击 UI Button（窗口失焦也能点） |

## 关键结论 / 陷阱

1. **走游戏自己的 API，不要手动 new 对象**。直接构造 `Segment` 会崩（原生层），
   而调用 `ClickAndDrag.CreateNewSegment(...)` 走游戏代码路径是安全的。
2. **反射选择器约定**：`obj:<instanceID>`、`path:/Name`、`type:<FullName>`
   （后者优先找静态单例字段 `instance/Instance/I/_instance/singleton/...`，否则取第一个活动实例）。
3. **合成鼠标事件（SendInput/mouse_event）Unity 不接收**：实测 OS 级点击无效；
   但「进程内点击 UI 按钮」和「直接调用游戏方法」都可靠。
4. **协程方法**（返回 `IEnumerator`）要用 `zen_coroutine` 才会真正执行；
   普通 `static void` 入口（如 `GameManager.BeginMainGame`）用 `zen_call` 即可。

## 实测操作序列（成功）

```
call type:GameManager BeginMainGame        # 进入编辑场景
call type:ClickAndDrag CreateNewSegment    # 反复调用，传入 parentID 链
   0,ID,null,length,speed,angle,drawTrail,trailWidth,color,pos,layerOrder,glow,isGradient,gradient,centerCam,openInfoP
shot mandala                               # 截图
```

36 段，长度递减、角度按黄金角 137.5° 旋转、HSV 渐变色，逐段 `parentID` 串成链。

## 接入 DSH

在 profile 的 `cordis.patch.yml` 追加一条 MCP client（与现有 ida/android/stellaris 同款）：

```yaml
- insert:
  - id: cc-switch-mcp-zentrails
    name: '@deepseek-ai/dsh-mcp-client'
    config:
      command: python
      args:
      - C:\Users\DC\ZenTrailsAgent\mcp_server.py
      serverName: zentrails
      transport: stdio
```

重启 DSH 会话后即可使用。手动验证：

```powershell
python C:\Users\DC\ZenTrailsAgent\mcp_server.py
# 然后按 MCP 协议发送 initialize / tools/list / tools/call
```

## 前置条件

- 游戏已启动（插件在 `Awake` 时监听 5123 端口）。
- 插件 DLL 在 `BepInEx\plugins\ZenTrailsAgent.dll`。
- 端口冲突可改 `AgentBridge.Port` 后重编译。

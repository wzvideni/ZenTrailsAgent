# Zen Trails AI 控制方案

让 AI Agent 通过 **MCP（Model Context Protocol）** 控制 Steam 游戏《Zen Trails》（Unity 2019.1 / Mono）。AI 直接调用游戏自身的 C# API 来绘制、修改、播放作品，并可用截图做视觉反馈。

提供基于 BepInEx 注入的进程内控制桥接与一套完整的标准 MCP 工具，支持进入编辑场景、程序化构建线段与复杂几何阵列、动态参数调优、纯净截图验证及 Steam 创意工坊直传。

## 架构

```
AI Agent（任意 MCP 客户端）
   │  MCP stdio（JSON-RPC 2.0）
   ▼
mcp_server.py  ──(line protocol / TCP 127.0.0.1:5123)──▶  ZenTrailsAgent.dll
                                                            (BepInEx 5 插件，游戏进程内)
                                                               │  Unity 主线程执行
                                                               ▼
                                                             游戏 C# API（反射调用）
```

- **游戏内插件**：`ZenTrailsAgent.dll` 注入到游戏进程，监听 `127.0.0.1:5123`，把每个命令放到 Unity 主线程 `Update()` 里执行，安全地反射调用游戏方法。
- **MCP server**：`zentrails_agent/server.py`（纯标准库 + Pillow），把桥协议封装成 15 个 MCP 工具。
- **客户端**：任何支持 MCP stdio 的客户端都能接入（Claude Desktop、Cursor、Cline、DSH 等）。

## 目录结构

```
ZenTrailsAgent/
├── AGENTS.md                # AI Agent 创作者指引（几何生成公式、创作工作流与神圣色彩体系）
├── src/
│   ├── AgentBridge.cs       # BepInEx 插件源码（C# 5，Framework csc 编译）
│   ├── Dump.cs              # 反射 API 转储工具源码（Cecil）
│   └── DumpIL.cs            # IL 反编译工具源码（Cecil）
├── zentrails_agent/         # Python 包（可安装，提供 zen-trails-agent 命令）
│   ├── __init__.py
│   ├── client.py            # 桥接客户端（TCP line protocol）
│   └── server.py            # MCP server（stdio / JSON-RPC 2.0，15 个工具）
├── docs/
│   └── INSTALL.txt          # 随发布包分发的安装/接入说明
├── demos/                   # 演示样例库
│   ├── celestial_multi_matrix_magic_circle.py # 演示：天衍神圣共鸣·万象生命之花复合大魔法阵（143段高阶流光）
│   ├── astral_dodecagram_magic_circle.py # 演示：十二重天体禁咒·终焉十二芒星与群星宿命大魔法阵（87段）
│   ├── flower_of_life_rosette.py         # 演示：折扇星芒与生命之花圣轮（-2逆速谐振）
│   ├── demo_draw.py         # 演示：程序化画线段
│   ├── demo_mandala.py      # 演示：黄金角曼陀罗（36 段）
│   └── demo_magic_circle.py # 演示：六芒星魔法阵（标准外摆线花瓣 + 内圈）
├── tools/
│   ├── probes/              # 诊断与探针脚本（check / draw / probe）
│   ├── build_plugin.ps1     # 编译 + 部署 + 重启游戏（一键）
│   ├── package.py           # 打发布包（编译插件 + 组装 MCP 服务 + 安装说明 → zip）
│   ├── paths.py             # 统一路径约定（仓库内相对定位，游戏目录可 ZEN_TRAILS_HOME 覆盖）
│   ├── dump_uploader.ps1    # IL 分析与反编译辅助工具
│   ├── test_tools.py        # MCP 工具端到端测试
│   ├── test_clickui.py      # UI 点击端到端测试
│   ├── test_upload.py       # 上传回归测试（验证先 Open 面板与截屏完整性的修复）
│   └── lib/                 # 逆向工具运行时依赖（从游戏拷贝，不进 git）
├── client.py                # 兼容 shim（等价于 zentrails_agent.client）
├── mcp_server.py            # 兼容 shim（等价于 zentrails_agent.server:main）
├── dist/                    # 编译产物 + 发布 zip（不进 git）
├── dumps/                   # 逆向中间产物（不进 git）
├── pyproject.toml           # uv 项目管理（含 [project.scripts] 入口）
└── .python-version
```

## 依赖

| 依赖 | 用途 | 获取方式 |
|------|------|----------|
| BepInEx 5 | 游戏插件运行时 | 游戏汉化补丁自带（`<游戏>/winhttp.dll` + `BepInEx/`） |
| csc（.NET Framework 4.x） | 编译插件 | Windows 自带：`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe` |
| Python ≥ 3.11 | 运行 MCP server | `uv` 管理（`uv sync` 创建 `.venv`，含 Pillow 并安装本包） |
| uv | 用 `uvx` 启动（可选） | `pip install uv` 或官方安装器 |
| Mono.Cecil | 逆向工具（可选） | 从游戏 `BepInEx\core\` 拷贝 |

## 构建

### 1. 编译插件

```powershell
# 仅编译（产物 dist/ZenTrailsAgent.dll）
pwsh -File tools/build_plugin.ps1
```

脚本引用游戏目录的 `BepInEx\core\BepInEx.dll` 与 `Zen Trails_Data\Managed\UnityEngine*.dll`，游戏路径写死在脚本顶部 `$game`，可按需修改。

### 2. 编译逆向工具（可选）

仅当需要静态分析游戏类型/IL 时：

```powershell
# 先把 Cecil 依赖拷进来
Copy-Item "<游戏>\BepInEx\core\Mono.Cecil*.dll" tools\lib\ -Force

# 编译反射转储工具
csc /out:tools\Dump.exe /r:tools\lib\Mono.Cecil.dll src\Dump.cs
# 编译 IL 反编译工具
csc /out:tools\DumpIL.exe /r:tools\lib\Mono.Cecil.dll src\DumpIL.cs

# 用法示例：转储游戏全部类型/成员
tools\Dump.exe "<游戏>\Zen Trails_Data\Managed\Assembly-CSharp.dll" dumps\api.txt
```

## 安装

### 1. 安装 Python 依赖

```powershell
cd path/to/ZenTrailsAgent
uv sync          # 创建 .venv、安装 Pillow，并把本包作为可执行命令 zen-trails-agent 装入 venv
```

验证命令已装好：

```powershell
uvx --from . zen-trails-agent --help   # 或：.\.venv\Scripts\zen-trails-agent.exe
```

### 2. 部署插件到游戏

```powershell
# 一键：编译 + 覆盖到游戏 plugins + 重启游戏
pwsh -File tools/build_plugin.ps1 -Deploy -Restart
```

或手动拷贝：

```powershell
Copy-Item dist\ZenTrailsAgent.dll "<游戏>\BepInEx\plugins\" -Force
```

### 3. 启动游戏

插件在 `Awake` 时监听 `127.0.0.1:5123`。游戏启动后可验证：

```powershell
& ".\.venv\Scripts\python.exe" -c "from client import Bridge; print(Bridge().cmd('ping')[1])"
# 期望输出：pong zen=<帧数> fps=60
```

## 打包分发

一键打出「可直接解压分发」的 zip：编译插件 + 组装 MCP 服务 + 写入安装说明。

```powershell
cd path/to/ZenTrailsAgent
uv run python tools/package.py               # 编译插件 + 打 zip
uv run python tools/package.py --no-rebuild  # 用已有 dist/ZenTrailsAgent.dll，不重编
uv run python tools/package.py --game <路径> # 指定游戏目录（默认 ZEN_TRAILS_HOME / Steam 常见位置）
```

产物：

```
dist/ZenTrails-Agent-v0.2.0.zip
    ZenTrails-Agent-v0.2.0/
        INSTALL.txt
        game/                              ← 解压覆盖到游戏根目录
            winhttp.dll  doorstop_config.ini  .doorstop_version
            BepInEx/core/                   ← BepInEx 5 运行时
            BepInEx/plugins/ZenTrailsAgent.dll
        mcp/                               ← MCP 服务，放任意目录，用 uvx 启动
            pyproject.toml
            zentrails_agent/…  client.py  mcp_server.py
```

- `game/` 的内容覆盖到游戏根目录即完成插件安装；`BepInEx` 运行时随包分发，目标机器无需预装汉化补丁。
- `mcp/` 是一个可被 `uvx` 直接构建的 Python 包，接入客户端时 `--from` 指向它即可（见下文「接入 MCP 客户端」）。
- zip 内顶层是版本目录，解压即得一个自包含目录，不污染解压位置的其他文件。

## 接入 MCP 客户端

在任意 MCP 客户端的配置里加入一个 `mcpServers` 条目（这是 Claude Desktop / Cursor / Cline 等通用的 JSON 格式）。项目已打包成可安装的 Python 包，提供 `zen-trails-agent` 命令，因此可以用 `uvx` 一行启动：

```json
{
  "mcpServers": {
    "zentrails": {
      "command": "uvx",
      "args": [
        "--from", "C:\\path\\to\\ZenTrailsAgent",
        "zen-trails-agent"
      ]
    }
  }
}
```

> 若把包发布到 PyPI，则可省略 `--from`，直接 `"command": "uvx"` + `"args": ["zen-trails-agent"]`（与 `uvx ida-mcp` 同款）。

备选方式（不依赖 `uvx`，直接调用 venv 里的 console script）：

```json
{
  "mcpServers": {
    "zentrails": {
      "command": "C:\\path\\to\\ZenTrailsAgent\\.venv\\Scripts\\zen-trails-agent.exe",
      "args": []
    }
  }
}
```

各客户端的落盘位置：

| 客户端 | 配置文件 |
|--------|----------|
| Claude Desktop | `claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` |
| Cline / Roo | 插件设置里的 MCP Servers（等价 JSON） |
| 其他 | 任何支持 `command` + `args` 的 stdio MCP 配置，内容等价 |

> 关于 `npx`：这是 Node 的等价物。本项目的 MCP server 是 Python 实现，用 `uvx` 是最自然的对应方式；若需要 `npx` 形式，需另写一个 Node 版 server（桥接协议不变，仅 client/server 换成 JS），目前未提供。

重启客户端后，工具列表会出现 `zentrails` 系列（包含 8 个高阶创作工具、5 个系统与工坊工具、10 个底层反射工具，共 23 个）。`mcp_server.py` 是懒连接：游戏没开时它不会崩，只是调用返回 `[ERR] bridge error`。

> 💡 **AI 创作必读**：关于物理多连杆逆旋摆线生成公式（生命之花、多芒星、日轮耀斑）及创作最佳实践，详见专为 Agent 编写的 **[AGENTS.md](file:///C:/Programming/PyCharm/ZenTrailsAgent/AGENTS.md)**。

## MCP 工具列表 (共 23 个)

### 1. 高阶领域创作工具（AI 创作核心）

| 工具 | 说明 |
|------|------|
| `zen_create_segment` | **高阶创建连杆**：自动补齐 16 个引擎参数、管理 ID、支持 `parent_id` 级联，自动隐藏机械网格并防原生崩溃 |
| `zen_clear` | **一键清空画布**：安全重置场景，清除所有活跃线段并复位 ID 计数器 |
| `zen_play` | **启动模拟**：确保解除暂停，运行物理模拟以绘制璀璨流光轨迹 |
| `zen_pause` | **定格画面**：通过 `TogglePause` 安全暂停物理运动，完好冻结流光画面，绝不抹除已绘制轨迹 |
| `zen_dark_mode` | **深邃夜空**：停用扰动背景，将主相机背景设为纯净宇宙黑（`0.02,0.02,0.04,1`） |
| `zen_set_camera` | **视角视距**：设置相机距离（如 `-10.5` 适合曼陀罗，`-12.8` 适合广角复合大魔法阵） |
| `zen_hide_arms` | **机械臂隐身**：一键隐藏物理连杆粗糙网格，仅在视口中展示纯净天体流光 |
| `zen_list_segments` | **查询骨架**：结构化查看当前画布全部线段的 ID、父子挂载关系、长度、转速、角度与颜色 |

### 2. 系统与工坊发布工具

| 工具 | 说明 |
|------|------|
| `zen_screenshot` | 截图到 `<游戏目录>\shots\*.png`；`return_image=true` 内联返回缩放 JPEG 供 vision 模型直读 |
| `zen_upload` | **工坊发布**：全自动无 UI 纯净拍摄（隐藏右上角导航栏）并推送到 Steam 创意工坊（30 秒冷却保护） |
| `zen_save` | 保存当前作品为 .mndla 二进制存档（type: custom/preset） |
| `zen_load` | 读取 .mndla 存档（反序列化 + SaveAndLoadManager.Load） |
| `zen_music` | 切换背景禅音（Mandalas/Wavelengths/Footprints/Dreams/Space，缺省切下一首） |

### 3. 底层调试与反射逃生通道

| 工具 | 说明 |
|------|------|
| `zen_cmd` | 通用桥协议命令（ping/types/describe/scene/find/get/set/call/coroutine/shot/mouse/drag/clickui/focus/log） |
| `zen_scene` | 转储场景层级（GameObject + 组件） |
| `zen_find` | 按类型列出活动实例（带 instance ID 和路径） |
| `zen_types` | 枚举游戏类型（可过滤子串） |
| `zen_describe` | 反射类型：字段 / 属性 / 方法 / 枚举 |
| `zen_get` | 读字段/属性（点路径，静态/实例均可） |
| `zen_set` | 写字段/属性（按声明类型转换，静态/实例均可） |
| `zen_call` | 调用普通方法（按参数类型转换） |
| `zen_coroutine` | 调用协程方法（`IEnumerator`），经 `StartCoroutine` 真正执行 |
| `zen_clickui` | 进程内点击 UI Button（窗口失焦也能点） |

### 反射选择器约定

- `obj:<instanceID>` —— 按实例 ID 定位
- `path:/Name` —— 按 GameObject 路径定位
- `type:<FullName>` —— 先找静态单例字段（`instance`/`Instance`/`I`/`_instance`/`singleton`/`Current`…），否则取第一个活动实例

## 关键结论 / 陷阱

1. **走游戏自己的 API，不要手动 new 对象**。直接构造 `Segment` 会触发原生崩溃；调用 `ClickAndDrag.CreateNewSegment(...)` 走游戏代码路径才是安全的。
2. **合成鼠标事件 Unity 不接收**：OS 级 `SendInput`/`mouse_event` 点击无效；「进程内点击 UI 按钮」（`zen_clickui`）和「直接调用游戏方法」都可靠。
3. **协程方法**（返回 `IEnumerator`）要用 `zen_coroutine` 才真正执行；普通 `static void` 入口（如 `GameManager.BeginMainGame`）用 `zen_call`。
4. **`gameState` 字段可能是残留值**，以 `zen_scene` 看到的实际场景为准（配合截图最可靠）。
5. **上传必须先 `Open()` 等待展开就绪，并触发官方截图按钮**。游戏原生 `Uploader.ieTakeScreenshot` 会在截图时自动隐藏右上角 `NavigationPanel` 导航栏与设置面板，截取完全零 UI 的画面并编码写入 `PreviewImage.jpg`；若面板未先 `Open()` 或未等待展开完成，会受到 `OpenWithCurtain` 动画影响导致把上传弹窗本身拍入画面；若在静态编辑态（未运转）截图则会因流光未生成而截得黑屏。`zen_upload` 工具现已内建完整时序：若处于未播放态自动运转定格流光 + 先 `Open()` 并等待展开就绪 + 触发官方截图按钮收起 UI 并完成编码 + 提交 `Upload()`。回归测试见 `tools/test_upload.py`。

## Steam 创意工坊自动化发布

`zen_upload` 工具打通了从「流光生成、无 UI 纯净定格截图、元数据写入」到「Steam UGC 提交发布」的全流程：

1. 自动检测模拟器状态，未运行时先运转绘制完整流光轨迹并使用 `TogglePause` 安全定格；
2. 展开上传面板，调用官方截图管线隐藏右上角导航栏与所有多余 UI，生成纯净 1080P `PreviewImage.jpg`；
3. 提交至 Steam 创意工坊并在完成后自动关闭弹窗恢复场景状态。

回归测试：

```powershell
uv run python tools/test_upload.py --skip-upload   # 只验证 Open/Close 状态机，不发送真实上传
uv run python tools/test_upload.py                 # 完整上传流程测试（含 30 秒冷却保护与自动收起断言）
```

## 几何艺术演示案例

仓库 `demos/` 目录下提供了多个可直接运行的高阶几何艺术与魔法阵案例：

| 案例脚本 | 节点数 | 特性与几何美学 |
|---------|-------|---------------|
| `demos/celestial_multi_matrix_magic_circle.py` | 143 段 | **天衍神圣共鸣·万象生命之花复合大魔法阵**：中枢十二瓣生命之花圣轮 + 六极星位卫星子法阵群（三曜真灵阵 / 四象星芒阵）+ 24 芒日轮耀斑外冠 |
| `demos/astral_dodecagram_magic_circle.py` | 87 段 | **天体禁咒·终焉十二芒星与群星宿命大魔法阵**：十二重同心天轨金界 + 双重交错十二芒星 + 曼陀罗莲华与八芒秘法结界 |
| `demos/flower_of_life_rosette.py` | 12 段 | **折扇星芒与生命之花圣轮**：6 根扇骨放射排布，子臂以 -2 倍速逆向谐振，划出倾角递增的生命之花金华圣轮 |
| `demos/demo_mandala.py` | 36 段 | **黄金角曼陀罗**：长度逐级递减、角度按黄金角 137.5° 螺旋排布、HSV 全彩渐变 |
| `demos/demo_magic_circle.py` | 24 段 | **六芒星外摆线魔法阵**：经典几何外摆线花瓣与多重内外防护圈 |
| `demos/demo_draw.py` | 4 段 | **基础测试**：简单单链连杆运动与轨迹记录 |

运行示例：

```powershell
# 运行天衍万象复合大魔法阵演示
uv run python demos/celestial_multi_matrix_magic_circle.py

# 运行经典黄金角曼陀罗
uv run python demos/demo_mandala.py
```

等价于用 MCP 工具循环执行 `zen_call`：

```
zen_call  selector=type:GameManager  method=BeginMainGame
zen_call  selector=type:ClickAndDrag  method=CreateNewSegment
  参数：isChild, ID, parentID, length, speed, angle,
        drawTrail, trailWidth, color, pos, layerOrder,
        glow, isGradient, gradient, centerCam, openInfoP
```

## 端口冲突

插件默认监听 `127.0.0.1:5123`，冲突时改 `src/AgentBridge.cs` 里的 `AgentPlugin.Port`，重新构建部署即可。

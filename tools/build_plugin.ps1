# 编译 AgentBridge.cs → dist/ZenTrailsAgent.dll，可选部署到游戏并重启。
# 用法:
#   pwsh -File tools/build_plugin.ps1            # 仅编译
#   pwsh -File tools/build_plugin.ps1 -Deploy    # 编译并部署到游戏 plugins
#   pwsh -File tools/build_plugin.ps1 -Deploy -Restart   # 部署后重启游戏进程
#
# 游戏目录默认取环境变量 ZEN_TRAILS_HOME，否则按 Steam 常见位置拼出来；
# 也可用 -Game 显式指定。
[CmdletBinding()]
param(
    [string]$Game = $(if ($env:ZEN_TRAILS_HOME) { $env:ZEN_TRAILS_HOME }
                      else { Join-Path ${env:ProgramFiles(x86)} 'Steam\steamapps\common\Zen Trails' }),
    [switch]$Deploy,
    [switch]$Restart
)

$ErrorActionPreference = 'Stop'

$root    = Split-Path -Parent $PSScriptRoot
$managed = Join-Path $Game 'Zen Trails_Data\Managed'
$core    = Join-Path $Game 'BepInEx\core'
$csc     = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$src     = Join-Path $root 'src\AgentBridge.cs'
$outDir  = Join-Path $root 'dist'
$outDll  = Join-Path $outDir 'ZenTrailsAgent.dll'

if (!(Test-Path $csc))   { throw "找不到 csc: $csc" }
if (!(Test-Path $src))   { throw "找不到源码: $src" }

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$refs = @(
    "$core\BepInEx.dll",
    "$managed\UnityEngine.CoreModule.dll",
    "$managed\UnityEngine.dll",
    "$managed\UnityEngine.ScreenCaptureModule.dll",
    "$managed\UnityEngine.UIModule.dll",
    "$managed\UnityEngine.UI.dll",
    'System.dll',
    'System.Core.dll'
) | ForEach-Object { "/r:$_" }

& $csc /nologo /target:library /platform:x64 /optimize+ /out:$outDll @refs $src
if ($LASTEXITCODE -ne 0) { throw "编译失败 (exit $LASTEXITCODE)" }

Write-Host "编译成功: $outDll" -ForegroundColor Green

if ($Deploy) {
    $plugins = Join-Path $Game 'BepInEx\plugins'
    # 覆盖 DLL 前必须停游戏（文件被进程锁定）
    Get-Process 'Zen Trails' -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1
    Copy-Item $outDll $plugins -Force
    Write-Host "已部署到: $plugins" -ForegroundColor Green

    if ($Restart) {
        Start-Process -FilePath (Join-Path $Game 'Zen Trails.exe') -WorkingDirectory $Game
        Write-Host "游戏已重启" -ForegroundColor Green
    }
}

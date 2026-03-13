# AI Config Sync

Windows 桌面工具，用一次操作把本地 `Skills` / `Commands` 分发到多个 AI 工具目录，并可选同步到同机 WSL2 的单个发行版。

当前版本已经移除 Electron，图形界面改为 Python + PySide6。

## 当前能力

- 只支持在 Windows 宿主上运行
- Python GUI 管理：
  - 概览
  - Skills
  - Skills 上游
  - Commands
  - 状态
  - 配置
  - 清理
  - 工具更新
- 同步目标支持：
  - Windows
  - 可选 WSL2 单发行版
- 同步方式支持：
  - 软链接 `symlink`
  - 文件复制 `copy`
- `copy` 模式下，同名目标会直接覆盖
- `Commands` 支持按工具配置“保留子目录 / 拍平目录”
- 工具更新支持 `npm` 包和自定义命令

## 运行环境

- Python 3.13+
- Windows

## 安装

```bash
python -m pip install -r requirements.txt
```

或使用虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 启动

### Windows

```bash
python -m python_app
```

或直接运行：

```bash
start.bat
```

### 非 Windows

不支持。`start.sh` 会直接退出并提示错误。

## GUI 说明

### 概览

- 查看当前同步模式
- 查看 WSL 开关与当前发行版
- 一键刷新
- 一键同步全部资源

### Skills / Commands

- 扫描源目录
- 点击工具矩阵立即同步或移除资源
- 同步当前类型的选中项

### Skills 上游

- 给本地 skill 绑定 GitHub 更新 URL（支持批量）
- 手动从 URL 下载 skill 到本地 Skills 源目录
- 检查最新 commit，并一键覆盖本地 skill 目录

### 状态

- 查看 Windows / WSL 环境状态
- 查看异常条目
- 查看最近动作日志

### 配置

- 修改 Skills / Commands 源目录
- 切换全局同步方式
- 开关 WSL 同步
- 选择 WSL 发行版
- 编辑 Windows / WSL 的目标目录
- 配置 Command 子目录支持规则

### 清理

- 清理冲突目标
- 清理缺失目标
- 清理源已失效的配置项

### 工具更新

- 按 `config.json` 中的 `updateTools` 批量执行更新

## 配置结构

`config.json` 保持现有结构不变：

```json
{
  "version": 2,
  "syncMode": "symlink",
  "sourceDirs": {
    "skills": "D:\\path\\to\\skills",
    "commands": "D:\\path\\to\\commands"
  },
  "environments": {
    "windows": {
      "enabled": true,
      "targets": {
        "skills": {
          "claude": "%USERPROFILE%\\.claude\\skills",
          "codex": "%USERPROFILE%\\.codex\\skills",
          "gemini": "%USERPROFILE%\\.gemini\\skills",
          "antigravity": "%USERPROFILE%\\.gemini\\antigravity\\skills"
        },
        "commands": {
          "claude": "%USERPROFILE%\\.claude\\commands",
          "codex": "%USERPROFILE%\\.codex\\prompts",
          "gemini": "%USERPROFILE%\\.gemini\\commands",
          "antigravity": "%USERPROFILE%\\.gemini\\antigravity\\global_workflows"
        }
      }
    },
    "wsl": {
      "enabled": false,
      "selectedDistro": null,
      "targets": {
        "skills": {
          "claude": "$HOME/.claude/skills",
          "codex": "$HOME/.codex/skills",
          "gemini": "$HOME/.gemini/skills",
          "antigravity": "$HOME/.gemini/antigravity/skills"
        },
        "commands": {
          "claude": "$HOME/.claude/commands",
          "codex": "$HOME/.codex/prompts",
          "gemini": "$HOME/.gemini/commands",
          "antigravity": "$HOME/.gemini/antigravity/global_workflows"
        }
      }
    }
  },
  "commandSubfolderSupport": {
    "default": false,
    "tools": {
      "claude": true
    }
  },
  "updateTools": {
    "Claude Code": {
      "type": "custom",
      "command": "claude update"
    },
    "Codex": {
      "type": "npm",
      "package": "@openai/codex"
    }
  }
}
```

说明：

- `syncMode` 为全局配置，同时作用于 Windows 与 WSL
- 资源分配（哪些 Skills / Commands 同步到哪些工具）存放在 `resources.json`
- Skill 上游更新（URL + 已安装 commit）存放在 `skill_sources.json`
- Windows 默认目标使用 `%USERPROFILE%` 占位符
- WSL 默认目标使用 `$HOME` 占位符

迁移说明：

- 从 `CONFIG_VERSION=3` 升级到 `CONFIG_VERSION=4` 后，若旧的 `config.json` 仍包含 `resources` 字段，程序会在启动时把它迁移到 `resources.json`，并自动重写 `config.json`（移除 `resources`）。

## WSL 同步说明

- 仅在 Windows 宿主上工作
- 通过 `wsl.exe` 发现发行版并读取 `$HOME`
- 实际文件写入使用 `\\\\wsl.localhost\\<distro>\\...` UNC 路径
- 若 WSL 未安装、发行版不存在或路径不可写，GUI 会明确显示错误

## 验证

```bash
python -m compileall python_app
python -m unittest discover -s tests -p "test_*.py"
```

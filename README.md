# AI Config Sync

Windows 桌面端，用一次操作把 Skills / Commands 同步到 Windows 本机，并可选同时同步到该 Windows 上安装的 WSL2 发行版。

## 当前能力

- 只支持在 Windows 上运行
- Electron GUI 管理：
  - 概览
  - Skills
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
- `copy` 模式下，同名目标在同步时会直接覆盖

## 安装

```bash
npm install
```

## 启动

### Windows

```bash
npm start
```

或直接运行：

```bash
start.bat
```

### 非 Windows

不支持。`start.sh` 和 `node index.js` 都会直接退出并提示错误。

## GUI 说明

### 概览

- 查看当前同步模式
- 查看 WSL 开关与当前发行版
- 一键刷新
- 一键同步全部资源

### Skills / Commands

- 扫描源目录
- 按工具分配资源
- 保存分配关系
- 同步当前类型的全部或选中项

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

`config.json` 当前使用新结构：

```json
{
  "version": 2,
  "syncMode": "symlink",
  "sourceDirs": {
    "skills": "/abs/path/to/skills",
    "commands": "/abs/path/to/commands"
  },
  "environments": {
    "windows": {
      "enabled": true,
      "targets": {
        "skills": {
          "claude": "%USERPROFILE%\\.claude\\skills"
        },
        "commands": {
          "claude": "%USERPROFILE%\\.claude\\commands"
        }
      }
    },
    "wsl": {
      "enabled": false,
      "selectedDistro": null,
      "targets": {
        "skills": {
          "claude": "$HOME/.claude/skills"
        },
        "commands": {
          "claude": "$HOME/.claude/commands"
        }
      }
    }
  },
  "resources": {
    "skills": {},
    "commands": {}
  }
}
```

说明：

- `syncMode` 为全局配置，同时作用于 Windows 与 WSL
- `resources.skills` / `resources.commands` 记录每个资源分配到哪些工具
- Windows 默认目标使用 `%USERPROFILE%` 占位符
- WSL 默认目标使用 `$HOME` 占位符

## WSL 同步说明

- 仅在 Windows 宿主上工作
- 通过 `wsl.exe` 发现发行版并读取 `$HOME`
- 实际文件写入使用 `\\\\wsl.localhost\\<distro>\\...` UNC 路径
- 若 WSL 未安装、发行版不存在或路径不可写，GUI 会明确显示错误，不做静默降级

## 构建校验

```bash
npm run typecheck
npm run build
```

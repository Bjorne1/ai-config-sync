## Why

用户需要一键更新 WSL 侧安装的 AI 开发工具（Claude Code、Codex、OpenSpec、Auggie 等），减少手动逐个执行 `npm update -g` 的繁琐操作。同时需要支持手动添加/删除自定义工具，以适应未来新增工具的场景。

## What Changes

- 新增「一键更新所有工具」菜单项，批量更新所有已配置的工具
- 新增「管理更新工具列表」菜单项，支持添加/删除自定义更新工具
- 更新前显示当前版本，更新后显示最新版本和更新结果
- 支持两种更新类型：
  - `npm`: 使用 `npm update -g <package>` 更新
  - `custom`: 使用自定义命令更新（如 `claude update`、`uv self update`）
- config.json 新增 `updateTools` 字段存储工具配置

## Capabilities

### New Capabilities
- `tool-updater`: 工具更新核心逻辑，包含版本检测、更新执行、结果展示

### Modified Capabilities
<!-- 无需修改现有 specs -->

## Impact

- **代码变更**:
  - `index.js`: 新增菜单项和对应的处理函数
  - `lib/config.js`: 新增默认工具配置和相关 getter/setter
- **配置变更**:
  - `config.json`: 新增 `updateTools` 字段
- **依赖**:
  - 无新增依赖，使用 Node.js 内置 `child_process` 执行更新命令

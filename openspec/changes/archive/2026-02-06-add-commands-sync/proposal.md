## Why

当前 Skill Manager 仅支持 Skills 文件的同步，但 AI 工具还有 Commands（自定义命令/提示词）需要跨工具管理。用户需要一种统一的方式将 Commands 从单一源目录同步到多个 AI 工具目录，同时处理各工具对子文件夹分类的不同支持程度。

## What Changes

- 新增 Commands 同步功能，与现有 Skills 同步功能并行独立运作
- 新增 Commands 源目录配置 (`commandsSourceDir`)，默认为 `./commands`
- 新增各工具的 Commands 目标目录映射:
  - Claude: `~/.claude/commands`
  - Codex: `~/.codex/prompts`
  - Gemini: `~/.gemini/commands`
  - Antigravity: `~/.gemini/antigravity/global_workflows`
- 新增子文件夹支持配置 (`commandSubfolderSupport`)，处理各工具对 Command 分类的差异化支持
- 新增交互式菜单项: 添加 Command / 禁用 Command / 移除 Command / 同步所有 Commands

## Capabilities

### New Capabilities
- `commands-sync`: Commands 文件同步核心能力，包括源目录扫描、目标目录映射、软链接创建/删除
- `subfolder-flatten`: 子文件夹扁平化处理，将 `{folder}/{file}.md` 转换为 `{folder}-{file}.md` 用于不支持分类的工具

### Modified Capabilities
（无现有 capability 需要修改）

## Impact

- `lib/config.js`: 新增 `DEFAULT_COMMAND_TARGETS`、`getCommandTargets()`、`getCommandSubfolderSupport()` 函数，扩展配置结构
- `lib/scanner.js`: 新增 `scanCommands()` 函数处理含子文件夹的命令扫描
- `index.js`: 新增 Command 相关菜单操作函数 (`addCommand`, `disableCommand`, `removeCommand`, `syncCommands`)
- `config.json`: 扩展配置结构，新增 `commandsSourceDir`、`commandTargets`、`commands`、`commandSubfolderSupport` 字段

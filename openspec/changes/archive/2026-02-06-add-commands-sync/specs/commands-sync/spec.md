## ADDED Requirements

### Requirement: Commands source directory configuration
系统 SHALL 支持配置 Commands 源目录 (`commandsSourceDir`)，默认为项目根目录下的 `commands` 文件夹。

#### Scenario: Default source directory
- **WHEN** 配置文件中未指定 `commandsSourceDir`
- **THEN** 系统使用 `{cwd}/commands` 作为 Commands 源目录

#### Scenario: Custom source directory
- **WHEN** 配置文件中指定了 `commandsSourceDir` 为 `/path/to/my-commands`
- **THEN** 系统使用 `/path/to/my-commands` 作为 Commands 源目录

### Requirement: Commands target directory mapping
系统 SHALL 为每个 AI 工具定义 Commands 目标目录。

#### Scenario: Claude target directory
- **WHEN** 同步 Command 到 Claude
- **THEN** 目标目录为 `~/.claude/commands`

#### Scenario: Codex target directory
- **WHEN** 同步 Command 到 Codex
- **THEN** 目标目录为 `~/.codex/prompts`

#### Scenario: Gemini target directory
- **WHEN** 同步 Command 到 Gemini
- **THEN** 目标目录为 `~/.gemini/commands`

#### Scenario: Antigravity target directory
- **WHEN** 同步 Command 到 Antigravity
- **THEN** 目标目录为 `~/.gemini/antigravity/global_workflows`

### Requirement: Commands scanning with subfolder support
系统 SHALL 扫描 Commands 源目录，仅识别 `.md` 文件和一级子文件夹。

#### Scenario: Scan top-level command files
- **WHEN** 源目录包含 `commit-quicker.md` 文件
- **THEN** 扫描结果包含 `{name: "commit-quicker.md", path: "...", isDirectory: false, parent: null}`

#### Scenario: Scan command subfolder
- **WHEN** 源目录包含 `gudaspec` 子文件夹，内有 `init.md`、`plan.md` 等 `.md` 文件
- **THEN** 扫描结果包含 `{name: "gudaspec", path: "...", isDirectory: true, children: ["init.md", "plan.md", ...]}`

#### Scenario: Skip non-markdown files
- **WHEN** 源目录包含 `config.json`、`README.txt` 等非 `.md` 文件
- **THEN** 扫描结果不包含这些文件

#### Scenario: Skip nested subfolders with warning
- **WHEN** 源目录包含二级嵌套结构 `folder/subfolder/file.md`
- **THEN** 系统仅扫描 `folder` 一级，忽略 `subfolder` 并在控制台输出警告 "⚠ 跳过二级嵌套: folder/subfolder"

### Requirement: Commands symlink creation
系统 SHALL 为选定的 Commands 创建软链接到目标工具目录。

#### Scenario: Create symlink for top-level command
- **WHEN** 用户选择将 `commit-quicker.md` 同步到 Claude
- **THEN** 创建软链接 `~/.claude/commands/commit-quicker.md` → `{sourceDir}/commit-quicker.md`

#### Scenario: Create symlink for command subfolder (tool supports subfolders)
- **WHEN** 用户选择将 `gudaspec` 文件夹同步到 Claude，且 Claude 支持子文件夹
- **THEN** 创建软链接 `~/.claude/commands/gudaspec` → `{sourceDir}/gudaspec`

### Requirement: Commands symlink removal
系统 SHALL 支持移除已创建的 Commands 软链接。

#### Scenario: Remove top-level command symlink
- **WHEN** 用户选择移除 Claude 的 `commit-quicker.md`
- **THEN** 删除软链接 `~/.claude/commands/commit-quicker.md`

#### Scenario: Remove subfolder command symlinks
- **WHEN** 用户选择移除 Codex 的 `gudaspec` 相关命令
- **THEN** 删除所有 `gudaspec-*.md` 软链接

### Requirement: Commands configuration persistence
系统 SHALL 在 `config.json` 中持久化 Commands 配置。

#### Scenario: Save enabled commands
- **WHEN** 用户启用 `commit-quicker.md` 到 Claude 和 Codex
- **THEN** 配置文件更新为 `commands: {"commit-quicker.md": ["claude", "codex"]}`

#### Scenario: Save subfolder commands
- **WHEN** 用户启用 `gudaspec` 文件夹到 Claude
- **THEN** 配置文件更新为 `commands: {"gudaspec": ["claude"]}`

### Requirement: Commands sync all
系统 SHALL 支持一键同步所有已配置的 Commands。

#### Scenario: Sync all commands
- **WHEN** 用户执行 "同步所有 Commands"
- **THEN** 系统遍历 `config.commands` 中所有条目，为每个工具验证/修复软链接

### Requirement: Skip uninstalled tools for commands
系统 SHALL 在同步 Commands 时跳过未安装的工具。

#### Scenario: Tool not installed
- **WHEN** 同步 Command 到 Gemini，但 `~/.gemini` 目录不存在
- **THEN** 跳过该工具并显示 "⚠ 工具未安装，已跳过"

### Requirement: Sync failure handling
系统 SHALL 在同步失败时继续执行其余工具，并汇总结果。

#### Scenario: Partial sync failure
- **WHEN** 同步 Command 到 4 个工具，其中 Claude 成功、Codex 权限失败、Gemini 成功、Antigravity 未安装
- **THEN** 系统继续执行所有工具，最终显示汇总: "✓ 2 成功 | ✗ 1 失败 | ⚠ 1 跳过"

#### Scenario: All tools fail
- **WHEN** 同步 Command 到所有工具均失败
- **THEN** 系统完成遍历后显示全部失败的汇总结果

### Requirement: Symlink conflict resolution
系统 SHALL 在目标位置存在非有效链接时覆盖创建新链接。

#### Scenario: Overwrite existing file/link
- **WHEN** 同步 `test.md` 到 Claude，`~/.claude/commands/test.md` 已存在（非有效链接）
- **THEN** 系统删除旧文件/链接，创建新的软链接

#### Scenario: Skip valid symlink
- **WHEN** 同步 `test.md` 到 Claude，`~/.claude/commands/test.md` 已是指向正确源的有效链接
- **THEN** 跳过创建，显示 "已存在有效链接"

## ADDED Requirements

### Requirement: Default tool configuration
系统 SHALL 提供默认的更新工具配置，包含以下工具：
- Claude Code: type=custom, command="claude update"
- Codex: type=npm, package="@openai/codex"
- OpenSpec: type=npm, package="@fission-ai/openspec"
- Auggie: type=npm, package="@augmentcode/auggie"
- ace-tool: type=npm, package="ace-tool"

#### Scenario: First run with no existing config
- **WHEN** config.json 中不存在 `updateTools` 字段
- **THEN** 系统 MUST 使用默认工具配置

#### Scenario: Custom config overrides default
- **WHEN** config.json 中存在 `updateTools` 字段
- **THEN** 系统 MUST 使用用户配置，不合并默认配置

### Requirement: Update all tools
用户 SHALL 能够通过菜单项「一键更新所有工具」批量更新所有已配置的工具。

#### Scenario: Menu item visibility
- **WHEN** 用户进入主菜单
- **THEN** MUST 显示「工具更新」分隔符和「一键更新所有工具」选项

#### Scenario: Execute update all
- **WHEN** 用户选择「一键更新所有工具」
- **THEN** 系统 MUST 串行执行每个工具的更新命令
- **AND** 对于 npm 类型工具，执行前 MUST 显示当前版本
- **AND** 更新完成后 MUST 显示最新版本和更新结果（成功/失败）
- **AND** 对于 custom 类型工具，MUST 显示执行状态（成功/失败）

#### Scenario: npm tool update
- **WHEN** 更新 type=npm 的工具
- **THEN** 系统 MUST 执行 `npm update -g <package>`

#### Scenario: custom tool update
- **WHEN** 更新 type=custom 的工具
- **THEN** 系统 MUST 执行配置中的 `command` 字段

#### Scenario: Update failure handling
- **WHEN** 某个工具更新失败
- **THEN** 系统 MUST 显示错误信息
- **AND** MUST 继续更新下一个工具，不中断整体流程

### Requirement: Manage update tools
用户 SHALL 能够添加、删除自定义更新工具。

#### Scenario: Add npm tool
- **WHEN** 用户选择「管理更新工具列表」→「添加工具」
- **AND** 选择 type=npm
- **THEN** 系统 MUST 提示输入工具名称和 npm 包名
- **AND** 保存到 config.json 的 `updateTools` 字段

#### Scenario: Add custom tool
- **WHEN** 用户选择「管理更新工具列表」→「添加工具」
- **AND** 选择 type=custom
- **THEN** 系统 MUST 提示输入工具名称和更新命令
- **AND** 保存到 config.json 的 `updateTools` 字段

#### Scenario: Remove tool
- **WHEN** 用户选择「管理更新工具列表」→「删除工具」
- **THEN** 系统 MUST 显示当前所有已配置工具列表供选择
- **AND** 用户选择后 MUST 从 config.json 删除对应配置

#### Scenario: View current tools
- **WHEN** 用户选择「管理更新工具列表」
- **THEN** 系统 MUST 显示当前所有已配置的工具及其类型

### Requirement: Version display for npm tools
对于 npm 类型工具，系统 SHALL 在更新前后显示版本信息。

#### Scenario: Get current version
- **WHEN** 更新 npm 类型工具前
- **THEN** 系统 MUST 使用 `npm list -g <package> --json` 获取当前版本

#### Scenario: Get latest version
- **WHEN** 更新 npm 类型工具后
- **THEN** 系统 MUST 使用 `npm list -g <package> --json` 获取更新后版本

#### Scenario: Version comparison display
- **WHEN** 更新完成
- **THEN** 系统 MUST 以表格形式显示：工具名 | 更新前版本 | 更新后版本 | 状态

## ADDED Requirements

### Requirement: Subfolder support configuration
系统 SHALL 通过 `commandSubfolderSupport` 配置控制各工具对 Command 子文件夹的支持。

#### Scenario: Default subfolder support
- **WHEN** 配置文件中未指定 `commandSubfolderSupport`
- **THEN** 系统使用默认配置 `{default: false, tools: {claude: true}}`

#### Scenario: Tool-level override
- **WHEN** 配置为 `{default: false, tools: {claude: true, codex: true}}`
- **THEN** Claude 和 Codex 支持子文件夹，Gemini 和 Antigravity 不支持

### Requirement: Subfolder flattening for unsupported tools
系统 SHALL 对不支持子文件夹的工具执行扁平化处理，将子文件夹内的文件以前缀方式重命名。

#### Scenario: Flatten subfolder commands
- **WHEN** 将 `gudaspec` 文件夹同步到 Codex（不支持子文件夹）
- **THEN** 为 `gudaspec/init.md` 创建软链接 `~/.codex/prompts/gudaspec-init.md`
- **AND** 为 `gudaspec/plan.md` 创建软链接 `~/.codex/prompts/gudaspec-plan.md`

#### Scenario: Top-level files unchanged
- **WHEN** 将 `commit-quicker.md`（顶层文件）同步到 Codex
- **THEN** 创建软链接 `~/.codex/prompts/commit-quicker.md`（无前缀）

### Requirement: Preserve subfolder structure for supported tools
系统 SHALL 对支持子文件夹的工具保留原始目录结构。

#### Scenario: Keep subfolder as symlink
- **WHEN** 将 `gudaspec` 文件夹同步到 Claude（支持子文件夹）
- **THEN** 创建单个目录软链接 `~/.claude/commands/gudaspec` → `{sourceDir}/gudaspec`

### Requirement: Check subfolder support before sync
系统 SHALL 在创建软链接前检查目标工具的子文件夹支持状态。

#### Scenario: Query subfolder support
- **WHEN** 准备同步 `gudaspec` 到 Codex
- **THEN** 系统查询 `commandSubfolderSupport.tools.codex`，若未定义则使用 `commandSubfolderSupport.default`

### Requirement: Flatten produces unique filenames
系统 SHALL 使用 `{folder}-{filename}` 格式生成扁平化后的文件名，确保唯一性。

#### Scenario: Naming convention
- **WHEN** 扁平化 `gudaspec/init.md`
- **THEN** 生成文件名为 `gudaspec-init.md`

#### Scenario: Multiple subfolders
- **WHEN** 扁平化 `folderA/test.md` 和 `folderB/test.md`
- **THEN** 生成文件名分别为 `folderA-test.md` 和 `folderB-test.md`

### Requirement: Flatten only markdown files
系统 SHALL 在扁平化子文件夹时仅处理 `.md` 文件。

#### Scenario: Skip non-markdown in subfolder
- **WHEN** 子文件夹 `gudaspec` 包含 `init.md`、`config.json`、`notes.txt`
- **THEN** 仅扁平化 `init.md`，跳过 `config.json` 和 `notes.txt`

### Requirement: Flatten conflict resolution
系统 SHALL 在扁平化命名冲突时覆盖现有链接。

#### Scenario: Flatten overwrites existing
- **WHEN** 源目录存在 `folderA/test.md` 和顶层 `folderA-test.md`
- **THEN** 扁平化时覆盖目标位置的现有链接，以子文件夹内的 `test.md` 为准

#### Scenario: Flatten target already linked
- **WHEN** 扁平化 `gudaspec/init.md`，目标 `~/.codex/prompts/gudaspec-init.md` 已存在旧链接
- **THEN** 删除旧链接并创建指向正确源的新链接

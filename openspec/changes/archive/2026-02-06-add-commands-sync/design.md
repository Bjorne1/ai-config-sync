## Context

当前 Skill Manager 已实现 Skills 同步功能，采用模块化架构：
- `lib/config.js`: 配置管理（DEFAULT_TARGETS、loadConfig、saveConfig）
- `lib/scanner.js`: 源目录扫描（scanSkills）
- `lib/linker.js`: 软链接操作（createSymlink、removeSymlink、isValidSymlink）
- `index.js`: 交互式菜单和用户操作

Commands 同步功能将复用现有架构模式，新增并行模块处理 Commands 特有的子文件夹逻辑。

## Goals / Non-Goals

**Goals:**
- 实现 Commands 独立同步功能，与 Skills 并行运作
- 支持 Commands 源目录可配置
- 处理各工具对子文件夹分类的差异化支持（Claude 支持，其他不支持）
- 提供交互式菜单操作 Commands

**Non-Goals:**
- 不修改现有 Skills 同步逻辑
- 不支持超过一层的子文件夹嵌套
- 不实现 Commands 内容编辑功能

## Decisions

### Decision 1: Commands 与 Skills 配置分离

**选择**: 在 `config.json` 中使用独立字段（`commandsSourceDir`、`commandTargets`、`commands`、`commandSubfolderSupport`）

**理由**:
- 职责清晰，避免混淆
- 便于独立管理和扩展
- 与现有 Skills 逻辑互不干扰

**备选**: 统一到单个 `items` 数组 + `type` 字段 —— 拒绝，增加复杂度

### Decision 2: 子文件夹支持配置结构

**选择**: `{default: boolean, tools: {toolName: boolean}}`

**理由**:
- 默认值 + 工具级覆盖，灵活应对未来变化
- 新工具支持子文件夹时只需修改配置
- 配置语义清晰

**默认值**: `{default: false, tools: {claude: true}}`

### Decision 3: 扁平化命名规则

**选择**: `{folder}-{filename}` 格式（如 `gudaspec-init.md`）

**理由**:
- 保留分类信息
- 避免不同文件夹同名文件冲突
- 命名规则简单直观

### Decision 4: 子文件夹同步粒度

**选择**:
- 支持子文件夹的工具: 整个文件夹作为一个软链接
- 不支持的工具: 展开为多个文件软链接

**理由**:
- 支持子文件夹时减少链接数量，便于管理
- 不支持时保持每个文件独立链接，符合工具预期

### Decision 5: Scanner 扩展方式

**选择**: 新增 `scanCommands()` 函数，返回结构包含 `children` 数组

**理由**:
- 不修改现有 `scanSkills()`，遵循开闭原则
- Commands 特有的子文件夹逻辑封装在新函数中

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 扁平化后文件名过长 | 仅保留一级文件夹名，不递归 |
| 用户误删手动创建的同名文件 | 仅操作软链接，拒绝删除非软链接文件 |
| 配置迁移 | 首次运行检测旧配置自动补全新字段 |
| 子文件夹内新增文件后同步不完整 | 同步时重新扫描源目录 |

## Test Properties (PBT)

### 关键不变量

| ID | 不变量 | 伪造策略 |
|----|--------|---------|
| P1.1 | `scanCommands()` 仅返回 `.md` 文件 | 创建混合类型源目录，断言结果不含非 `.md` 文件 |
| P1.2 | 扫描尊重一级嵌套限制 | 创建二级嵌套结构，断言深层文件被跳过并输出警告 |
| P2.1 | `flattenCommandName()` 输出全局唯一 | 生成 1000+ (folder, file) 组合，断言无哈希冲突 |
| P4.1 | `syncCommands()` 幂等性 | 连续调用两次同步，断言第二次无实际变更 |
| P6.3 | 同步失败继续执行 | 模拟部分工具权限失败，断言其他工具仍被处理 |

### 边界条件

- 空子文件夹: 扫描结果包含 `children: []`，同步跳过
- 特殊字符路径: 文件夹/文件名含 `-`、`_`、数字时扁平化正确
- 最大路径长度: Windows 260 字符限制下的处理

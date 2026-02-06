## 1. 配置模块扩展 (lib/config.js)

- [x] 1.1 新增 `DEFAULT_COMMAND_TARGETS` 常量，定义各工具 Commands 目标目录映射
- [x] 1.2 新增 `getDefaultCommandsSourceDir()` 函数，返回默认 Commands 源目录
- [x] 1.3 新增 `getCommandTargets(config)` 函数，合并默认和自定义 Command 目标目录
- [x] 1.4 新增 `getCommandSubfolderSupport(config, tool)` 函数，查询工具的子文件夹支持状态
- [x] 1.5 更新 `initConfig()` 函数，初始化 Commands 相关配置字段
- [x] 1.6 导出新增函数

## 2. 扫描模块扩展 (lib/scanner.js)

- [x] 2.1 新增 `scanCommands(sourceDir)` 函数，扫描 Commands 源目录
- [x] 2.2 实现仅扫描 `.md` 文件的过滤逻辑
- [x] 2.3 实现子文件夹识别，返回包含 `children` 数组的结构
- [x] 2.4 实现二级嵌套检测并输出警告 "⚠ 跳过二级嵌套: {path}"
- [x] 2.5 导出 `scanCommands` 函数

## 3. 子文件夹扁平化逻辑 (lib/scanner.js 或新模块)

- [x] 3.1 新增 `flattenCommandName(folderName, fileName)` 函数，生成扁平化文件名
- [x] 3.2 新增 `expandCommandsForTool(commands, tool, subfolderSupport)` 函数，根据工具支持状态展开命令列表

## 4. 菜单操作函数 (index.js)

- [x] 4.1 新增 `addCommand(cfg)` 函数，实现添加 Command 交互流程
- [x] 4.2 新增 `disableCommand(cfg)` 函数，实现禁用 Command 交互流程
- [x] 4.3 新增 `removeCommand(cfg)` 函数，实现移除 Command 交互流程
- [x] 4.4 新增 `syncCommands(cfg)` 函数，实现同步所有 Commands（含冲突覆盖逻辑）
- [x] 4.5 新增 `showCommandStatus(cfg)` 函数，显示 Commands 状态表格
- [x] 4.6 实现同步结果汇总显示 "✓ N 成功 | ✗ N 失败 | ⚠ N 跳过"

## 5. 菜单集成 (index.js)

- [x] 5.1 在 `showMenu()` 中添加 Command 相关菜单项
- [x] 5.2 在 switch 语句中处理新菜单选项
- [x] 5.3 更新快捷命令支持 `sync-commands`

## 6. 测试验证

- [x] 6.1 手动测试顶层 Command 文件同步到所有工具
- [x] 6.2 手动测试子文件夹同步到 Claude（保留结构）
- [x] 6.3 手动测试子文件夹同步到 Codex（扁平化）
- [x] 6.4 验证配置持久化和重新加载
- [x] 6.5 测试二级嵌套警告输出
- [x] 6.6 测试非 `.md` 文件被正确跳过
- [x] 6.7 测试部分工具失败时继续执行并汇总
- [x] 6.8 测试冲突覆盖场景（目标已存在非有效链接）

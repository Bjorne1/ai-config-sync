## 1. 配置模块扩展

- [x] 1.1 在 `lib/config.js` 中添加 `DEFAULT_UPDATE_TOOLS` 常量，包含默认工具配置
- [x] 1.2 在 `lib/config.js` 中添加 `getUpdateTools(config)` 函数，返回更新工具配置
- [x] 1.3 在 `lib/config.js` 中添加 `saveUpdateTools(config, tools)` 函数，保存工具配置

## 2. 更新执行模块

- [x] 2.1 创建 `lib/updater.js` 模块
- [x] 2.2 实现 `getNpmVersion(packageName)` 函数，使用 `npm list -g <pkg> --json` 获取当前版本
- [x] 2.3 实现 `updateNpmTool(packageName)` 函数，执行 `npm update -g <package>`
- [x] 2.4 实现 `updateCustomTool(command)` 函数，执行自定义更新命令
- [x] 2.5 实现 `updateAllTools(tools)` 函数，串行更新所有工具并收集结果

## 3. 菜单集成

- [x] 3.1 在 `index.js` 的 `showMenu` 函数中添加「工具更新」分隔符和菜单项
- [x] 3.2 实现 `updateAllToolsMenu(cfg)` 函数，调用 updater 模块并显示结果表格
- [x] 3.3 实现 `manageUpdateTools(cfg)` 函数，提供添加/删除/查看子菜单

## 4. 工具管理交互

- [x] 4.1 实现 `addUpdateTool(cfg)` 函数，引导用户输入工具名称、类型和配置
- [x] 4.2 实现 `removeUpdateTool(cfg)` 函数，显示工具列表供用户选择删除
- [x] 4.3 实现 `listUpdateTools(cfg)` 函数，显示当前所有已配置工具

## 5. 测试验证

- [x] 5.1 验证菜单项正确显示
- [x] 5.2 验证一键更新功能正常执行
- [x] 5.3 验证添加/删除工具功能正常工作
- [x] 5.4 验证 config.json 正确保存配置

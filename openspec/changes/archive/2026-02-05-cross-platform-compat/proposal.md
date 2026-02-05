## Why

项目最初为 Windows 平台开发，现需支持 WSL/Linux 用户。当前代码存在平台特定假设（权限错误码、用户提示信息），导致在 Linux 环境下无法正常使用。

## What Changes

- 修改权限错误检测逻辑，同时支持 Windows (`EPERM`) 和 Linux (`EACCES`) 错误码
- 根据运行平台显示对应的权限不足解决方案提示
- 新增 `start.sh` 脚本供 WSL/Linux 用户使用
- 更新 README 文档，补充跨平台使用说明

## Capabilities

### New Capabilities

- `platform-detection`: 运行时平台检测与适配，包括错误码识别和提示信息切换

### Modified Capabilities

无。本次修改不涉及现有规格层面的行为变更，仅为平台兼容性适配。

## Impact

- `lib/linker.js`: 权限检查函数需兼容双平台错误码
- `index.js`: 权限提示信息需根据平台动态生成
- 新增 `start.sh`: Linux/WSL 启动脚本
- `README.md`: 文档更新

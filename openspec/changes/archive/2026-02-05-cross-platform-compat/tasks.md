## 1. lib/linker.js 修改

- [x] 1.1 修改 `checkSymlinkPermission()` 函数，同时检查 `EPERM` 和 `EACCES` 错误码
- [x] 1.2 修改 `createSymlink()` 函数，同时检查 `EPERM` 和 `EACCES` 错误码

## 2. index.js 修改

- [x] 2.1 添加平台检测辅助函数 `isWindows()`
- [x] 2.2 创建平台相关的权限提示信息
- [x] 2.3 修改权限不足时的提示逻辑，根据平台显示对应提示

## 3. 启动脚本

- [x] 3.1 创建 `start.sh` 脚本供 Linux/WSL 使用

## 4. 文档更新

- [x] 4.1 更新 README.md，补充跨平台使用说明

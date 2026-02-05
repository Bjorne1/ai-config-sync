### Requirement: Platform detection

系统 SHALL 在运行时检测当前操作系统平台，区分 Windows 和 Linux/WSL 环境。

#### Scenario: Windows environment detection
- **WHEN** 程序在 Windows 环境下运行
- **THEN** `process.platform` 返回 `'win32'`，系统识别为 Windows 平台

#### Scenario: WSL/Linux environment detection
- **WHEN** 程序在 WSL 或原生 Linux 环境下运行
- **THEN** `process.platform` 返回 `'linux'`，系统识别为 Linux 平台

### Requirement: Cross-platform permission error detection

系统 SHALL 同时识别 Windows (`EPERM`) 和 Linux (`EACCES`) 的权限错误码。

#### Scenario: Windows permission error
- **WHEN** 在 Windows 上创建软链接失败且错误码为 `EPERM`
- **THEN** 系统识别为权限不足错误

#### Scenario: Linux permission error
- **WHEN** 在 Linux/WSL 上创建软链接失败且错误码为 `EACCES`
- **THEN** 系统识别为权限不足错误

### Requirement: Platform-specific permission hints

系统 SHALL 根据当前平台显示对应的权限问题解决方案。

#### Scenario: Windows permission hint
- **WHEN** 在 Windows 上检测到权限不足
- **THEN** 显示 "以管理员身份运行" 或 "启用开发者模式" 的解决方案

#### Scenario: Linux permission hint
- **WHEN** 在 Linux/WSL 上检测到权限不足
- **THEN** 显示 "检查目标目录权限" 或 "使用 sudo" 的解决方案

### Requirement: Cross-platform startup scripts

系统 SHALL 提供各平台对应的启动脚本。

#### Scenario: Windows startup
- **WHEN** 用户在 Windows 上运行 `start.bat`
- **THEN** 以管理员权限启动程序

#### Scenario: Linux startup
- **WHEN** 用户在 Linux/WSL 上运行 `./start.sh`
- **THEN** 正常启动程序

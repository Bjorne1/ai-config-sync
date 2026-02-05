## Context

Skill Manager 是一个 CLI 工具，通过软链接同步 skill 文件到各 AI 工具配置目录。当前实现仅考虑 Windows 平台：
- 权限错误检测仅处理 `EPERM`
- 错误提示仅提供 Windows 解决方案
- 仅提供 `start.bat` 启动脚本

## Goals / Non-Goals

**Goals:**
- 支持在 Windows 和 WSL/Linux 环境下正常运行
- 根据平台提供适当的错误提示
- 提供各平台对应的启动脚本

**Non-Goals:**
- 不支持跨文件系统软链接（WSL 访问 /mnt/c）
- 不支持 macOS（暂时）
- 不修改核心 symlink 创建逻辑（Node.js 已处理 type 参数兼容性）

## Decisions

### 1. 平台检测方式

使用 `process.platform` 检测运行环境：
- `'win32'` → Windows
- 其他 → Linux/WSL

**理由**：Node.js 内置 API，无需额外依赖，WSL 环境下返回 `'linux'`。

### 2. 权限错误码处理

同时检查 `EPERM`（Windows）和 `EACCES`（Linux）。

**理由**：两个平台使用不同错误码表示权限不足，需要兼容处理。

### 3. 提示信息策略

创建平台相关的提示信息对象，运行时根据平台选择。

**理由**：集中管理提示信息，便于维护和扩展。

## Risks / Trade-offs

- **[Risk] WSL 与 Windows 共享 Home 目录场景** → 不在本次支持范围，文档明确说明
- **[Trade-off] 不检测具体 Linux 发行版** → 简化实现，通用提示足够

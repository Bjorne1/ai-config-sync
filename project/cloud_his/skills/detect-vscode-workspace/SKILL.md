---
name: detect-vscode-workspace
description: Use when working in /home/wcs/projects/work-project/cloud_his and you need to identify the VSCode workspace bound to the current Codex conversation window, especially when multiple workspace windows are open.
---

# detect-vscode-workspace

识别当前这次对话绑定的 VSCode 窗口对应的 workspace，并读取对应的 `.code-workspace` 文件内容。

## 使用边界

- 仅用于仓库：`/home/wcs/projects/work-project/cloud_his`
- 默认只判断当前 Codex 会话绑定的那个 VSCode 窗口
- 不默认枚举所有已打开窗口
- 依赖当前会话能够追溯到 VSCode `extensionHost`
- 如果 `workspaceStorage`、服务名或 workspace 文件无法唯一确定，直接失败，不猜

## 入口脚本

`/home/wcs/projects/work-project/cloud_his/.agents/skills/detect-vscode-workspace/scripts/detect_current_workspace.sh`

## 用法

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/detect-vscode-workspace/scripts/detect_current_workspace.sh"
```

只输出 workspace 文件路径：

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/detect-vscode-workspace/scripts/detect_current_workspace.sh" --path-only
```

只输出 workspace 文件内容：

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/detect-vscode-workspace/scripts/detect_current_workspace.sh" --content-only
```

## 判定方式

1. 从当前进程祖先链或 `VSCODE_IPC_HOOK_CLI` 找到当前窗口的 `extensionHost`
2. 从该进程打开的 `remoteexthost.log` 和 `workspaceStorage` 反查当前窗口的存储目录
3. 优先读取该 `workspaceStorage` 下 `vscjava.vscode-maven/*.deps.txt` 的首行，直接识别当前服务
4. 如果依赖文件不足，再回退到当前窗口自己的 Java/Git/Maven 日志里找唯一服务名
5. 将服务名映射为仓库根目录下的 `<service>-dev.code-workspace`
6. 输出路径与文件内容

## 失败信号

- `Unable to locate current VSCode extensionHost`
- `Unable to resolve unique workspaceStorage`
- `Unable to resolve unique service`
- `Workspace file not found`

## 说明

- 支持 `workspaceStorage/<hash>-1` 这种同一 workspace 多窗口场景
- 这个 skill 的目标是定位“当前对话绑定窗口”，不是列出全部窗口

---
name: deploy-cloud-service
description: Use when working in /home/wcs/projects/work-project/cloud_his and the user wants to deploy ai, drg, emr, his, interface, pay, report, or xxl services.
---

# deploy-cloud-service

统一执行 `cloud_his` 下 `wh-modules` 微服务的打包、复制和结果校验。

## 使用边界

- 仅用于仓库：`/home/wcs/projects/work-project/cloud_his`
- 默认复用 `detect-vscode-workspace` 能力，按当前 Codex 会话绑定的 VSCode 窗口识别服务
- 部署目标只包含：
  - `ai-service`
  - `drg-service`
  - `emr-service`
  - `his-service`
  - `interface-service`
  - `pay-service`
  - `report-service`
  - `xxl-job-admin`
- 如果服务无法唯一确定，直接报错，不要猜
- 不要通过扫描仓库内的 `*.code-workspace` 来猜“当前打开的工作区”；只允许复用 `detect-vscode-workspace` 的判定结果

## 入口脚本

优先使用脚本，不要手写长 Maven 命令：

`/home/wcs/projects/work-project/cloud_his/.agents/skills/deploy-cloud-service/scripts/deploy_service.sh`

## 执行方式

### 显式指定服务

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/deploy-cloud-service/scripts/deploy_service.sh" ai
```

### 按上下文推断

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/deploy-cloud-service/scripts/deploy_service.sh"
```

无参数时按以下顺序解析：

1. 当前 Codex 会话绑定的 VSCode 工作区
2. 当前 `cwd` 是否位于 `wh-modules/<service>` 下

如果两者都无法唯一确定，直接失败。
如果两者同时命中但不是同一个服务，也直接失败，不猜。

### 显式传入工作区文件

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/deploy-cloud-service/scripts/deploy_service.sh" --workspace-file "/home/wcs/projects/work-project/cloud_his/drg-service-dev.code-workspace"
```

仅在调用方已经明确拿到活动 workspace 文件路径时使用。

### 仅验证解析结果

```bash
"/home/wcs/projects/work-project/cloud_his/.agents/skills/deploy-cloud-service/scripts/deploy_service.sh" --dry-run drg
```

## 约束

- 始终使用 JDK8：`/home/wcs/.local/opt/jdk8`
- Maven 命令统一为：`mvn clean package -pl <module> -am -DskipTests=true -Dmaven.test.skip=true`
- 构建成功后必须复制 jar 到：`/mnt/e/deploy-project/`
- 回答用户时要带验证证据：
  - 实际部署的服务名
  - Maven 命令
  - 产物路径
  - Windows 目标路径

## 服务别名

- `ai` -> `ai-service`
- `drg` -> `drg-service`
- `emr` -> `emr-service`
- `his` -> `his-service`
- `interface` -> `interface-service`
- `pay` -> `pay-service`
- `report` -> `report-service`
- `xxl` -> `xxl-job-admin`

## 默认解析顺序

1. 用户显式输入的服务别名或服务名
2. 调用方显式传入的 `--workspace-file`
3. 当前 Codex 会话绑定的 VSCode 工作区
4. 当前 `cwd` 是否位于 `wh-modules/<service>` 下

若以上都无法唯一解析，必须显式失败。
如果第 3 步和第 4 步同时命中但结果不同，也必须显式失败。

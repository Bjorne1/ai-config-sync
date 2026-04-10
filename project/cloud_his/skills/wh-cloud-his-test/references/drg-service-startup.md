# drg-service 启动特例

`drg-service` 在这个仓库里是已知特殊服务。测试前先看 `.vscode/launch.json`，不要直接套 `ai-service` 的启动方式。

## 当前已知启动链路

VSCode 启动配置里，`drg-service` 使用了这些关键参数：

- `preLaunchTask: prepare-drg-wsl-config`
- `-Dspring.profiles.active=wcs`
- `-Dspring.cloud.nacos.config.enabled=false`
- `-Dspring.config.additional-location=file:${workspaceFolder}/.vscode/runtime/drg-service-wcs.runtime.yaml`

这意味着它不是普通的：

- `dev`
- `DEFAULT_GROUP`
- 启动后再实时从 Nacos 拉配置

## prepare 脚本实际做了什么

脚本路径：

- `/home/wcs/projects/work-project/cloud_his/.vscode/scripts/prepare-drg-wsl-config.sh`

它会做两件事：

1. 从 Nacos 拉取 `drg-service-wcs.yaml`
2. 生成本地 runtime yaml，并把 `wh_drg` 的 JDBC URL 改写成当前 WSL 默认网关 IP

所以这个脚本的重点不只是“下载配置”，而是把远程 `wcs` 配置改造成当前 WSL 能直接连接数据库的本地运行配置。

## 测试时的要求

- 如果用户要真实启动 `drg-service` 联调，优先按 launch 配置等价执行。
- 如果 launch 已经关闭 `spring.cloud.nacos.config.enabled`，就不要再假设服务运行时还会去 Nacos 拉配置。
- 如果用户问“为什么 drg-service 要 prepare，而 ai-service 不用”，默认解释为：
  - `drg-service` 的本地启动链路被定制成了 `wcs + 本地 runtime yaml + WSL DB 地址改写`
  - `ai-service` 当前仍可直接用远程 `dev/DEFAULT_GROUP` 配置启动

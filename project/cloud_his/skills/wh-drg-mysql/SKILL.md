---
name: wh-drg-mysql
description: 连接并查询本机 MySQL 数据库 wh_drg（wh_drg_read 只读账号，自动适配 Windows/WSL 环境）。当需要测试连接、执行 SQL 查询、查看表结构/表数据，或用户提到 wh_drg/DRG/MySQL 查询时使用。
---

# wh-drg-mysql

## 使用方式（给 Claude）

- 优先用 `python3 scripts/mysql_query.py` 执行连接测试与查询，不要手写长 `mysql` 命令。
- 默认连接信息：`127.0.0.1:3306` / `wh_drg_read` / `wh_drg_read` / `wh_drg`。
- 此账号为只读账号（无 DELETE 权限）；遇到 `INSERT/UPDATE/DDL` 先向用户确认再执行。
- 需要改连接信息时，用环境变量覆盖：`WH_DRG_MYSQL_HOST` `WH_DRG_MYSQL_PORT` `WH_DRG_MYSQL_USER` `WH_DRG_MYSQL_PASSWORD` `WH_DRG_MYSQL_DATABASE`（也支持通用 `MYSQL_HOST` 等）。

## WSL 自动适配

脚本自动检测运行环境：
- **Windows**：直接使用 `127.0.0.1` 连接本机 MySQL。
- **WSL（默认）**：优先使用 Linux 原生 `mysql`；若未安装，则优先使用 `PyMySQL` 直连。
- **WSL + Windows mysql.exe**：只有检测到当前会话的 Windows 互操作可正常启动时才会使用；若互操作卡住，会明确跳过并打印原因，不再阻塞查询。
- **WSL 主机地址**：当使用 Linux `mysql` 或 `PyMySQL` 时，脚本会自动通过 `ip route` 获取 Windows 宿主网关 IP（每次 WSL 启动动态变化），替换 `127.0.0.1`。

无需手动配置，两个平台都能直接用。

## 快速命令

- 连接测试：`python3 scripts/mysql_query.py --test`
- 执行 SQL：`python3 scripts/mysql_query.py --sql "SHOW TABLES;"`
- 执行 SQL 文件：`python3 scripts/mysql_query.py --sql-file path/to/query.sql`

## 常用查询模板

- 列出表：`SHOW TABLES;`
- 查看表结构：`DESCRIBE table_name;`
- 预览数据：`SELECT * FROM table_name LIMIT 10;`
- 条件查询：`SELECT col1, col2 FROM table_name WHERE ... LIMIT 100;`

## 故障排查

- **WSL 连不上**：确认 Windows 上 MySQL 服务已启动；确认 MySQL `bind-address` 为 `0.0.0.0`（非 `127.0.0.1`）；确认 `wh_drg_read` 用户允许从非 localhost 连接（`GRANT ... TO 'wh_drg_read'@'%'`）。
- **WSL 下没有 mysql**：优先执行 `python3 -m pip install --user PyMySQL`；也可自行安装 Linux `mysql` 客户端。
- **找不到 mysql**：先确认 `mysql --version` 可用；必要时设置 `MYSQL_EXE` 环境变量指向 mysql.exe 完整路径。
- **强制指定驱动**：可通过 `--driver auto|mysql|pymysql` 或环境变量 `WH_DRG_MYSQL_DRIVER` 覆盖自动策略。

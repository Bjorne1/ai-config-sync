---
name: wh-drg-mysql
description: 连接并查询本机 MySQL 数据库 wh_drg（默认 127.0.0.1:3306，root/root）。当需要测试连接、执行 SQL 查询、查看表结构/表数据，或用户提到 wh_drg/DRG/MySQL 查询时使用。
---

# wh-drg-mysql

## 使用方式（给 Claude）

- 优先用 `scripts/mysql_query.py` 执行连接测试与查询，不要手写长 `mysql` 命令。
- 默认连接信息：`127.0.0.1:3306` / `root` / `root` / `wh_drg`。
- 需要改连接信息时，优先用环境变量覆盖：`WH_DRG_MYSQL_HOST` `WH_DRG_MYSQL_PORT` `WH_DRG_MYSQL_USER` `WH_DRG_MYSQL_PASSWORD` `WH_DRG_MYSQL_DATABASE`（也支持通用 `MYSQL_HOST` `MYSQL_PORT` `MYSQL_USER` `MYSQL_PASSWORD` `MYSQL_DATABASE`）。
- 只读为主；遇到 `INSERT/UPDATE/DELETE/DDL` 先向用户确认再执行。

## 快速命令

- 连接测试：在本 skill 目录下运行 `python scripts/mysql_query.py --test`
- 执行 SQL：`python scripts/mysql_query.py --sql "SHOW TABLES;"`
- 执行 SQL 文件：`python scripts/mysql_query.py --sql-file path\\to\\query.sql`

## 常用查询模板

- 列出表：`SHOW TABLES;`
- 查看表结构：`DESCRIBE table_name;`
- 预览数据：`SELECT * FROM table_name LIMIT 10;`
- 条件查询：`SELECT col1, col2 FROM table_name WHERE ... LIMIT 100;`

## 故障排查

- 找不到 `mysql`：先确认 `mysql --version` 可用；必要时设置 `MYSQL_EXE` 为 `mysql.exe` 完整路径，或把 MySQL `bin` 加到 `PATH`。


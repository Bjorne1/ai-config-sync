# MySQL Schema Introspection

当 `sql-to-bean` 以“数据库名 + 表名”模式工作时，优先用这里的方式获取结构。

## wh_drg 场景

先加载 `wh-drg-mysql` skill，然后优先用它的脚本：

```powershell
python "C:\Users\Administrator\.codex\skills\wh-drg-mysql\scripts\mysql_query.py" --test
```

下面示例里的 `drg_cc` 只是演示表名；实际使用时替换成用户指定的表名。

## 优先查询：SHOW CREATE TABLE

这是首选方式。它能直接返回完整建表语句，最适合复用 DDL 解析流程。

如果不确定表是否存在，先做一次存在性检查：

```powershell
python "C:\Users\Administrator\.codex\skills\wh-drg-mysql\scripts\mysql_query.py" --database wh_drg --no-header --sql "SHOW TABLES LIKE 'drg_cc';"
```

```powershell
python "C:\Users\Administrator\.codex\skills\wh-drg-mysql\scripts\mysql_query.py" --database wh_drg --sql "SHOW CREATE TABLE `drg_cc`;"
```

如果用户说的是 `wh-drg` 数据库，应先规范化为 `wh_drg` 再执行。

## 结构化补充查询

当你需要更稳定地读取表注释、列注释、可空、主键、长度和默认值时，再补查 `information_schema`。

查询表注释：

```powershell
python "C:\Users\Administrator\.codex\skills\wh-drg-mysql\scripts\mysql_query.py" --database wh_drg --no-header --sql "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'wh_drg' AND TABLE_NAME = 'drg_cc';"
```

查询列结构：

```powershell
python "C:\Users\Administrator\.codex\skills\wh-drg-mysql\scripts\mysql_query.py" --database wh_drg --no-header --sql "SELECT COLUMN_NAME, COLUMN_TYPE, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, COLUMN_COMMENT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'wh_drg' AND TABLE_NAME = 'drg_cc' ORDER BY ORDINAL_POSITION;"
```

## 使用建议

1. 先用 `SHOW CREATE TABLE`，再把结果当成 DDL 解析
2. 只有在注释、主键、可空等信息不清晰时，才补查 `information_schema`
3. 不要只用 `DESCRIBE table_name;`，因为它没有注释
4. 不要用 `SELECT * FROM table_name LIMIT 10;` 倒推字段结构
5. 如果数据库不可达或当前会话没有该库连接能力，显式要求用户提供 DDL
6. 如果 `SHOW TABLES LIKE ...` 没有结果，说明表不存在，应直接告诉用户，不要生成占位代码

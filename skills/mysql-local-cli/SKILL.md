---
name: mysql-local-cli
description: Use when you need to query the local MySQL database (127.0.0.1:3306, db wh_drg) with the provided root/root credentials and MySQL 5.7 bin path; covers schema introspection and running SELECT/DDL/DML via mysql CLI.
---

# Local MySQL CLI (wh_drg)

Purpose: quickly run MySQL queries against the local `wh_drg` database using the bundled MySQL 5.7 client.

## Quick start (PowerShell)

```powershell
# Make mysql client available for this session
$env:Path += ";C:\Program Files\MySQL\MySQL Server 5.7\bin"

# Run a query against wh_drg
mysql -h127.0.0.1 -P3306 -u root -proot -D wh_drg -e "SHOW TABLES;"
```

## Common snippets

- Describe table:  
  `mysql -h127.0.0.1 -P3306 -u root -proot -D wh_drg -e "DESCRIBE dip_aux_disease;"`

- Sample rows:  
  `mysql -h127.0.0.1 -P3306 -u root -proot -D wh_drg -e "SELECT * FROM dip_aux_score LIMIT 10;"`

- Filtered query template:  
  `mysql -h127.0.0.1 -P3306 -u root -proot -D wh_drg -e "SELECT * FROM <table> WHERE <condition> LIMIT 50;"`

- Multi-statement query (quote the whole block):
  ```powershell
  $sql = @"
  SELECT 'dip_aux_disease' AS tbl;
  SELECT * FROM dip_aux_disease LIMIT 5;
  SELECT 'dip_aux_score' AS tbl;
  SELECT * FROM dip_aux_score LIMIT 5;
  "@
  mysql -h127.0.0.1 -P3306 -u root -proot -D wh_drg -e $sql
  ```

## Notes

- Credentials and host: `root` / `root`, host `127.0.0.1`, port `3306`, database `wh_drg`.
- If you need another shell, prepend the bin path the same way (e.g., in Git Bash: `export PATH=\"$PATH:/c/Program\\ Files/MySQL/MySQL\\ Server\\ 5.7/bin\"`).
- Avoid putting the password in logs; if needed, use `mysql_config_editor` for stored creds, but inline `-proot` is acceptable for quick ad-hoc use in this environment.

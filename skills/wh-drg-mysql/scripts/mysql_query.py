#!/usr/bin/env python3
import argparse
import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WSL_MYSQL_EXE_CANDIDATES = [
    "/mnt/c/Program Files/MySQL/MySQL Server 5.7/bin/mysql.exe",
    "/mnt/c/Program Files/MySQL/MySQL Server 8.0/bin/mysql.exe",
    "/mnt/c/Program Files/MySQL/MySQL Server 8.4/bin/mysql.exe",
]

LOCALHOST_ADDRESSES = {"127.0.0.1", "localhost", "::1"}

DEFAULT_USER = "wh_drg_read"
DEFAULT_PASSWORD = "wh_drg_read"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3306
DEFAULT_DATABASE = "wh_drg"
DEFAULT_INTEROP_TIMEOUT_SECONDS = 2
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _env_int(*names: str) -> int | None:
    value = _first_env(*names)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _is_wsl() -> bool:
    """Detect WSL by checking /proc/version for 'microsoft'."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def _is_windows_executable(path: str) -> bool:
    return path.lower().endswith(".exe")


def _get_windows_host_ip() -> str | None:
    """Get Windows host IP from WSL via default gateway (dynamic per boot)."""
    try:
        output = subprocess.check_output(
            ["ip", "route", "show", "default"], text=True,
        )
        parts = output.strip().split()
        return parts[2] if len(parts) >= 3 else None
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return None


def _import_pymysql():
    try:
        import pymysql
        from pymysql.constants import CLIENT
    except ImportError:
        return None, None
    return pymysql, CLIENT


def _windows_mysql_candidates() -> list[str]:
    candidates: list[str] = []
    for candidate in WSL_MYSQL_EXE_CANDIDATES:
        if Path(candidate).exists():
            candidates.append(candidate)
    return candidates


def _can_run_windows_mysql(path: str, timeout_seconds: int) -> tuple[bool, str | None]:
    try:
        completed = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return False, "文件不存在"
    except PermissionError as exc:
        return False, str(exc)
    except subprocess.TimeoutExpired:
        return False, f"启动超过 {timeout_seconds}s，当前 WSL 会话的 Windows 互操作不可用"

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        message = stderr or stdout or f"退出码 {completed.returncode}"
        return False, message
    return True, None


def _resolve_driver(
    explicit_mysql_path: str | None,
    requested_driver: str,
) -> tuple[str, str | None]:
    env_mysql_path = _first_env(
        "WH_DRG_MYSQL_EXE", "MYSQL_EXE",
        "WH_DRG_MYSQL_BIN", "MYSQL_BIN",
    )
    mysql_path = explicit_mysql_path or env_mysql_path
    pymysql, _ = _import_pymysql()

    if requested_driver == "pymysql":
        if pymysql is None:
            raise RuntimeError(
                "已显式指定 PyMySQL，但当前环境未安装。"
                "请执行 `python3 -m pip install --user PyMySQL`。"
            )
        return "pymysql", None

    if requested_driver == "mysql":
        resolved_path = mysql_path or shutil.which("mysql")
        if not resolved_path:
            raise FileNotFoundError(
                "已显式指定 mysql 客户端，但当前环境未找到 `mysql`。"
            )
        if _is_wsl() and _is_windows_executable(resolved_path):
            ok, reason = _can_run_windows_mysql(
                resolved_path, DEFAULT_INTEROP_TIMEOUT_SECONDS,
            )
            if not ok:
                raise RuntimeError(
                    f"WSL 下无法启动 Windows mysql.exe: {reason}"
                )
        return "mysql", resolved_path

    native_mysql = mysql_path or shutil.which("mysql")
    if native_mysql and not (_is_wsl() and _is_windows_executable(native_mysql)):
        return "mysql", native_mysql

    if pymysql is not None:
        if _is_wsl():
            print(
                "[WSL] 使用 PyMySQL 直连 Windows 宿主 MySQL，跳过 Windows 互操作。",
                file=sys.stderr,
            )
        return "pymysql", None

    windows_candidates = []
    if _is_wsl():
        windows_candidates = _windows_mysql_candidates()
        for candidate in windows_candidates:
            ok, reason = _can_run_windows_mysql(
                candidate, DEFAULT_INTEROP_TIMEOUT_SECONDS,
            )
            if ok:
                print(
                    f"[WSL] Windows 互操作可用，使用 {candidate}",
                    file=sys.stderr,
                )
                return "mysql", candidate
            print(
                f"[WSL] 跳过 {candidate}：{reason}",
                file=sys.stderr,
            )

    if native_mysql:
        return "mysql", native_mysql

    if _is_wsl():
        raise RuntimeError(
            "WSL 下未找到可用的 MySQL 客户端。"
            "当前会话的 Windows 互操作不可用，且本机没有 Linux `mysql`，"
            "也没有安装 PyMySQL。请执行 `python3 -m pip install --user PyMySQL`，"
            "或安装 Linux mysql 客户端。"
        )

    raise FileNotFoundError(
        "未找到可用的 mysql 客户端；请先确保 `mysql --version` 可用，"
        "或安装 PyMySQL。"
    )


def _resolve_host(host: str, driver: str, mysql_executable: str | None) -> str:
    """In WSL, localhost must be remapped unless using a working Windows mysql.exe."""
    if not _is_wsl():
        return host
    if driver == "mysql" and mysql_executable and _is_windows_executable(mysql_executable):
        return host
    if host not in LOCALHOST_ADDRESSES:
        return host

    windows_ip = _get_windows_host_ip()
    if windows_ip:
        print(
            f"[WSL] 将 {host} 替换为 Windows 宿主 IP: {windows_ip}",
            file=sys.stderr,
        )
        return windows_ip

    print(
        f"[WSL] 警告：无法获取 Windows 宿主 IP，保持 {host}",
        file=sys.stderr,
    )
    return host


def _write_defaults_file(
    host: str,
    port: int,
    user: str,
    password: str | None,
) -> str:
    lines = ["[client]", f"host={host}", f"port={port}", f"user={user}"]
    if password is not None:
        lines.append(f"password={password}")
    content = "\n".join(lines) + "\n"

    file_handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="wh-drg-mysql-",
        suffix=".cnf",
        delete=False,
    )
    try:
        file_handle.write(content)
        return file_handle.name
    finally:
        file_handle.close()


def _build_mysql_command(
    mysql_executable: str,
    defaults_file: str,
    database: str,
    no_header: bool,
) -> list[str]:
    command = [
        mysql_executable,
        f"--defaults-extra-file={defaults_file}",
        "--protocol=tcp",
        f"--connect-timeout={DEFAULT_CONNECT_TIMEOUT_SECONDS}",
        f"--database={database}",
        "--batch",
        "--raw",
    ]
    if no_header:
        command.append("--skip-column-names")
    return command


def _print_rows(rows: list[tuple], columns: list[str], no_header: bool) -> None:
    writer = csv.writer(
        sys.stdout,
        delimiter="\t",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    if not no_header and columns:
        writer.writerow(columns)
    for row in rows:
        writer.writerow(["NULL" if value is None else value for value in row])


def _execute_via_pymysql(
    host: str,
    port: int,
    user: str,
    password: str | None,
    database: str,
    sql: str,
    no_header: bool,
) -> int:
    pymysql, client = _import_pymysql()
    if pymysql is None or client is None:
        raise RuntimeError(
            "当前环境未安装 PyMySQL。"
            "请执行 `python3 -m pip install --user PyMySQL`。"
        )

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        connect_timeout=DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout=None,
        write_timeout=None,
        client_flag=client.MULTI_STATEMENTS,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            has_result = cursor.execute(sql)
            while True:
                columns = []
                rows = []
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    rows = list(cursor.fetchall())
                elif has_result:
                    rows = list(cursor.fetchall())
                if columns or rows:
                    _print_rows(rows, columns, no_header)
                if not cursor.nextset():
                    break
    finally:
        connection.close()
    return 0


def _read_sql(sql: str | None, sql_file: str | None) -> str:
    if sql is not None:
        return sql
    if not sql_file:
        raise ValueError("Missing SQL source")

    sql_path = Path(sql_file)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL 文件不存在：{sql_path}")
    return sql_path.read_text(encoding="utf-8")


def main() -> int:
    default_host = _first_env("WH_DRG_MYSQL_HOST", "MYSQL_HOST") or DEFAULT_HOST
    default_port = _env_int("WH_DRG_MYSQL_PORT", "MYSQL_PORT") or DEFAULT_PORT
    default_user = _first_env("WH_DRG_MYSQL_USER", "MYSQL_USER") or DEFAULT_USER
    default_pw = _first_env("WH_DRG_MYSQL_PASSWORD", "MYSQL_PASSWORD") or DEFAULT_PASSWORD
    default_db = _first_env("WH_DRG_MYSQL_DATABASE", "MYSQL_DATABASE") or DEFAULT_DATABASE

    parser = argparse.ArgumentParser(
        prog="mysql_query.py",
        description=f"Query MySQL ({DEFAULT_DATABASE}@{DEFAULT_HOST}:{DEFAULT_PORT}).",
    )
    parser.add_argument("--host", default=default_host)
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--user", default=default_user)
    parser.add_argument("--password", default=default_pw)
    parser.add_argument("--database", default=default_db)
    parser.add_argument(
        "--mysql", dest="mysql_exe", default=None,
        help="Path to mysql executable.",
    )
    parser.add_argument(
        "--driver",
        choices=("auto", "mysql", "pymysql"),
        default=_first_env("WH_DRG_MYSQL_DRIVER", "MYSQL_DRIVER") or "auto",
        help="Database driver strategy.",
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--sql", default=None, help="SQL to execute.")
    source_group.add_argument("--sql-file", default=None, help="Path to .sql file.")
    source_group.add_argument(
        "--test", action="store_true",
        help="Run connection test (SELECT 1, DATABASE()).",
    )
    parser.add_argument("--no-header", action="store_true", help="Suppress column names.")

    args = parser.parse_args()

    sql: str | None = None
    sql_file: str | None = None
    if args.test:
        sql = "SELECT 1 AS ok, DATABASE() AS db;"
    elif args.sql is not None:
        sql = args.sql
    else:
        sql_file = args.sql_file

    driver, mysql_executable = _resolve_driver(args.mysql_exe, args.driver)
    resolved_host = _resolve_host(args.host, driver, mysql_executable)
    query_sql = _read_sql(sql, sql_file)

    if driver == "pymysql":
        return _execute_via_pymysql(
            host=resolved_host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database,
            sql=query_sql,
            no_header=args.no_header,
        )

    defaults_file = _write_defaults_file(
        host=resolved_host, port=args.port,
        user=args.user, password=args.password,
    )

    try:
        command = _build_mysql_command(
            mysql_executable=mysql_executable,
            defaults_file=defaults_file,
            database=args.database,
            no_header=args.no_header,
        )

        if sql is not None:
            command.extend(["--execute", query_sql])
            completed = subprocess.run(command, check=False)
            return int(completed.returncode)

        with Path(sql_file).open("rb") as input_stream:
            completed = subprocess.run(command, stdin=input_stream, check=False)
            return int(completed.returncode)
    finally:
        try:
            Path(defaults_file).unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import argparse
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


def _resolve_mysql_executable(explicit_path: str | None) -> str:
    if explicit_path:
        return explicit_path

    env_path = _first_env(
        "WH_DRG_MYSQL_EXE", "MYSQL_EXE",
        "WH_DRG_MYSQL_BIN", "MYSQL_BIN",
    )
    if env_path:
        return env_path

    # In WSL, prefer Windows mysql.exe for seamless localhost connectivity
    if _is_wsl():
        for candidate in WSL_MYSQL_EXE_CANDIDATES:
            if Path(candidate).exists():
                return candidate

    which_path = shutil.which("mysql")
    if which_path:
        return which_path

    # Non-WSL Windows fallback
    if not _is_wsl():
        for candidate in WSL_MYSQL_EXE_CANDIDATES:
            win_path = candidate.replace("/mnt/c/", r"C:\\").replace("/", "\\")
            if Path(win_path).exists():
                return win_path

    raise FileNotFoundError(
        "未找到 mysql 可执行文件；请先确保 `mysql --version` 可用，"
        "或设置环境变量 MYSQL_EXE 指向 mysql.exe 完整路径。"
    )


def _resolve_host(host: str, mysql_executable: str) -> str:
    """In WSL with native mysql client, resolve localhost to Windows host IP."""
    if not _is_wsl():
        return host
    if mysql_executable.lower().endswith(".exe"):
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
        f"--database={database}",
        "--batch",
        "--raw",
    ]
    if no_header:
        command.append("--skip-column-names")
    return command


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

    mysql_executable = _resolve_mysql_executable(args.mysql_exe)
    resolved_host = _resolve_host(args.host, mysql_executable)

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
            command.extend(["--execute", sql])
            completed = subprocess.run(command, check=False)
            return int(completed.returncode)

        if not sql_file:
            raise ValueError("Missing --sql-file")

        sql_path = Path(sql_file)
        if not sql_path.exists():
            raise FileNotFoundError(f"SQL 文件不存在：{sql_path}")

        with sql_path.open("rb") as input_stream:
            completed = subprocess.run(command, stdin=input_stream, check=False)
            return int(completed.returncode)
    finally:
        try:
            Path(defaults_file).unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

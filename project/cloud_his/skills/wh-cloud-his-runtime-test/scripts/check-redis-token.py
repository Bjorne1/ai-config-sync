#!/usr/bin/env python3
"""Redis token 校验：从服务配置解析真实 Redis 地址，校验连通性 + token 存在性。

退出码: 0=pass, 1=fail, 2=参数错误, 3=Redis 不可达
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parent.parent
REPO_ROOT = SCRIPT_PATH.parents[4]
DEFAULT_MATRIX_PATH = SKILL_ROOT / "contracts" / "service-capability-matrix.yaml"
PLACEHOLDER_PATTERN = re.compile(r"^\$\{[^:}]+:([^}]+)\}$")

REDIS_KEY_PREFIX = "TOKEN:SYS:"
DEFAULT_TOKEN = "codex-cloud-his-dev-token"

# 矩阵级默认值（仅在配置文件中完全找不到时回退）
FALLBACK_REDIS_HOST = "192.168.10.206"
FALLBACK_REDIS_PORT = 6379
FALLBACK_REDIS_PASSWORD = "FJwhrj.888"


def fail(message, code=1):
    sys.stderr.write(f"{message}\n")
    raise SystemExit(code)


def load_yaml(path_text):
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        fail(f"未找到服务能力矩阵: {path}", 2)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_services(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("services"), list):
            return raw["services"]
        if all(isinstance(v, dict) for v in raw.values()):
            result = []
            for name, value in raw.items():
                item = dict(value)
                item.setdefault("service_name", name)
                result.append(item)
            return result
    return []


def get_service_entry(matrix_data, service_name):
    for entry in normalize_services(matrix_data):
        if entry.get("service_name") == service_name:
            return entry
    fail(f"服务能力矩阵中不存在服务: {service_name}", 2)


def resolve_repo_path(candidate):
    if not candidate:
        return None
    path = Path(str(candidate)).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def extract_path_candidates(service_entry):
    candidates = []
    for key in ("runtime_file", "runtime_config", "profile_config_path", "config_path"):
        value = service_entry.get(key)
        if value:
            candidates.append(value)
    launch_sources = service_entry.get("launch_sources") or []
    if isinstance(launch_sources, str):
        launch_sources = [launch_sources]
    for source in launch_sources:
        if isinstance(source, str) and source.endswith((".yaml", ".yml")):
            candidates.append(source)
        elif isinstance(source, dict):
            for k in ("path", "file", "runtime_file", "config_path", "profile_config_path"):
                v = source.get(k)
                if v:
                    candidates.append(v)
    module_path = service_entry.get("module_path")
    service_name = service_entry.get("service_name", "")
    if module_path:
        module_dir = resolve_repo_path(module_path)
        if module_dir:
            for fb in (
                module_dir / "src/main/resources/bootstrap-emr.yaml",
                module_dir / "src/main/resources/bootstrap-wh.yaml",
                module_dir / "src/main/resources/bootstrap-wcs.yaml",
                module_dir / "src/main/resources/bootstrap.yaml",
            ):
                candidates.append(str(fb))
    if service_name == "drg-service":
        candidates.append(str(REPO_ROOT / ".vscode/runtime/drg-service-wcs.runtime.yaml"))
    ordered = []
    seen = set()
    for c in candidates:
        path = resolve_repo_path(c)
        if path and path not in seen:
            ordered.append(path)
            seen.add(path)
    return ordered


def nested_get(data, key_path):
    current = data
    for part in key_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def resolve_placeholder(value):
    """解析 Spring 占位 ${xxx:default} 取 default 部分。"""
    if not isinstance(value, str):
        return value
    m = PLACEHOLDER_PATTERN.match(value.strip())
    return m.group(1) if m else value


def resolve_redis_connection(service_entry, cli_overrides):
    """从服务配置中解析 Redis host/port/password/db。

    优先级: CLI 覆盖 > 配置文件 > 矩阵默认 > 全局回退。
    """
    host = cli_overrides.get("host")
    port = cli_overrides.get("port")
    password = cli_overrides.get("password")
    db = cli_overrides.get("db")
    source_info = {}

    # 从矩阵 redis_db_rule 中尝试取 db
    rule = service_entry.get("redis_db_rule")
    if isinstance(rule, dict):
        for k in ("db", "database", "value", "default", "env_default"):
            if db is not None:
                break
            v = rule.get(k)
            if v is not None:
                try:
                    db = int(resolve_placeholder(v))
                    source_info["db"] = f"matrix:{k}"
                except (ValueError, TypeError):
                    pass

    # 从配置文件解析
    key_map = {
        "host": ["spring.redis.host", "redis.host"],
        "port": ["spring.redis.port", "redis.port"],
        "password": ["spring.redis.password", "redis.password"],
        "db": ["spring.redis.database", "redis.database"],
    }
    if isinstance(rule, dict):
        for field in ("yaml_key", "key"):
            extra = rule.get(field)
            if extra:
                key_map["db"].insert(0, extra)

    for candidate in extract_path_candidates(service_entry):
        if not candidate.is_file():
            continue
        with candidate.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}

        for field, keys in key_map.items():
            current = {"host": host, "port": port, "password": password, "db": db}[field]
            if current is not None:
                continue
            for kp in keys:
                raw = nested_get(content, kp)
                if raw is not None:
                    resolved = resolve_placeholder(raw)
                    if field in ("port", "db"):
                        try:
                            resolved = int(resolved)
                        except (ValueError, TypeError):
                            continue
                    if field == "host":
                        host = resolved
                    elif field == "port":
                        port = resolved
                    elif field == "password":
                        password = resolved
                    elif field == "db":
                        db = resolved
                    source_info.setdefault(field, f"{candidate.name}:{kp}")
                    break

        # emr profile 默认 db=1
        rule_type = rule.get("type") if isinstance(rule, dict) else rule
        if db is None and rule_type == "from_profile_config":
            if candidate.name.endswith(("-emr.yaml", "-emr.yml")):
                db = 1
                source_info.setdefault("db", f"{candidate.name}:profile_default_emr")

    # 回退到全局默认
    if host is None:
        host = FALLBACK_REDIS_HOST
        source_info.setdefault("host", "fallback_default")
    if port is None:
        port = FALLBACK_REDIS_PORT
        source_info.setdefault("port", "fallback_default")
    if password is None:
        password = FALLBACK_REDIS_PASSWORD
        source_info.setdefault("password", "fallback_default")
    if db is None:
        fail("未能解析 Redis DB 号；请检查服务矩阵或配置文件", 2)

    return {
        "host": host,
        "port": int(port),
        "password": password,
        "db": int(db),
        "source": source_info,
    }


def redis_cli_base(conn):
    cmd = ["redis-cli", "-h", conn["host"], "-p", str(conn["port"])]
    if conn["password"]:
        cmd.extend(["-a", conn["password"]])
    cmd.extend(["-n", str(conn["db"])])
    return cmd


def check_connectivity(conn):
    """PING Redis，返回 (reachable, latency_ms, error)。"""
    cmd = redis_cli_base(conn) + ["PING"]
    try:
        import time
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        latency = int((time.time() - start) * 1000)
        stdout = result.stdout.strip()
        # redis-cli 在带密码时输出可能带 Warning 行
        lines = [l for l in stdout.split("\n") if not l.startswith("Warning")]
        response = lines[-1] if lines else ""
        if "PONG" in response:
            return True, latency, None
        return False, latency, response or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, 10000, "连接超时"
    except OSError as e:
        return False, 0, str(e)


def check_token(conn, token):
    """检查 token key 是否存在，返回 (exists, ttl, preview)。"""
    redis_key = f"{REDIS_KEY_PREFIX}{token}"
    base = redis_cli_base(conn)

    # EXISTS
    result = subprocess.run(base + ["EXISTS", redis_key], capture_output=True, text=True, timeout=10)
    exists_out = result.stdout.strip().split("\n")
    exists_line = [l for l in exists_out if not l.startswith("Warning")]
    exists = exists_line[-1].strip() == "1" if exists_line else False

    if not exists:
        return False, None, None

    # TTL
    result = subprocess.run(base + ["TTL", redis_key], capture_output=True, text=True, timeout=10)
    ttl_out = [l for l in result.stdout.strip().split("\n") if not l.startswith("Warning")]
    try:
        ttl = int(ttl_out[-1].strip()) if ttl_out else None
    except ValueError:
        ttl = None

    # GET preview (前 200 字符)
    result = subprocess.run(base + ["GET", redis_key], capture_output=True, text=True, timeout=10)
    get_out = [l for l in result.stdout.strip().split("\n") if not l.startswith("Warning")]
    preview = get_out[-1][:200] if get_out else ""

    return True, ttl, preview


def main():
    parser = argparse.ArgumentParser(description="Redis token 校验：从服务配置解析地址，检查连通性和 token")
    parser.add_argument("--service", required=True, help="服务名")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX_PATH))
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--redis-host", help="覆盖 Redis host")
    parser.add_argument("--redis-port", type=int, help="覆盖 Redis port")
    parser.add_argument("--redis-password", help="覆盖 Redis password")
    parser.add_argument("--redis-db", type=int, help="覆盖 Redis DB")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    matrix_data = load_yaml(args.matrix)
    service_entry = get_service_entry(matrix_data, args.service)

    cli_overrides = {}
    if args.redis_host:
        cli_overrides["host"] = args.redis_host
    if args.redis_port:
        cli_overrides["port"] = args.redis_port
    if args.redis_password:
        cli_overrides["password"] = args.redis_password
    if args.redis_db is not None:
        cli_overrides["db"] = args.redis_db

    conn = resolve_redis_connection(service_entry, cli_overrides)

    result = {
        "service": args.service,
        "redis_host": conn["host"],
        "redis_port": conn["port"],
        "redis_db": conn["db"],
        "redis_source": conn["source"],
        "connectivity": None,
        "latency_ms": None,
        "token": args.token,
        "token_exists": False,
        "token_ttl": None,
        "token_preview": None,
        "verdict": "fail",
    }

    reachable, latency, err = check_connectivity(conn)
    result["connectivity"] = "ok" if reachable else "unreachable"
    result["latency_ms"] = latency

    if not reachable:
        result["verdict"] = "redis_unreachable"
        result["error"] = err
        _emit(result, args.json_output)
        sys.exit(3)

    exists, ttl, preview = check_token(conn, args.token)
    result["token_exists"] = exists
    result["token_ttl"] = ttl
    result["token_preview"] = preview

    if exists:
        result["verdict"] = "pass"
        _emit(result, args.json_output)
        sys.exit(0)
    else:
        result["verdict"] = "token_missing"
        _emit(result, args.json_output)
        sys.exit(1)


def _emit(data, as_json):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        v = data["verdict"]
        conn_str = f"{data['redis_host']}:{data['redis_port']}/db{data['redis_db']}"
        if v == "pass":
            print(f"[pass] token 存在 @ {conn_str} (TTL={data['token_ttl']})")
        elif v == "redis_unreachable":
            print(f"[fail] Redis 不可达: {conn_str} — {data.get('error', '')}")
        else:
            print(f"[fail] token 不存在 @ {conn_str}")
        print(f"  地址来源: {data['redis_source']}")


if __name__ == "__main__":
    main()

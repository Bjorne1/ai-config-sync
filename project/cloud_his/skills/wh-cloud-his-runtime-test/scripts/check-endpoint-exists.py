#!/usr/bin/env python3
"""目标接口存在性校验：按优先级检查 /v2/api-docs → 启动日志 → 业务接口直探。

退出码: 0=found, 1=not_found, 2=参数错误, 3=所有检查源不可达
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def fetch_api_docs(port, api_docs_path, timeout):
    """通过 curl 获取 swagger api-docs JSON。"""
    url = f"http://localhost:{port}{api_docs_path}"
    try:
        result = subprocess.run(
            ["curl", "-sf", "--connect-timeout", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout), True
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None, False


def check_in_api_docs(swagger, endpoint, method):
    """在 swagger paths 中查找目标接口（精确匹配 + 前缀匹配）。"""
    paths = swagger.get("paths", {})
    method_lower = method.lower()

    # 精确匹配
    if endpoint in paths:
        methods = {k.lower() for k in paths[endpoint]}
        if method_lower in methods:
            return {"found": True, "match": "exact"}

    # 前缀匹配（控制器家族）
    best_prefix = ""
    for path_key in paths:
        normalized = path_key.rstrip("/")
        if endpoint.startswith(normalized + "/") and len(normalized) > len(best_prefix):
            methods = {k.lower() for k in paths[path_key]}
            if method_lower in methods:
                best_prefix = normalized

    if best_prefix:
        return {"found": True, "match": "prefix", "matched_prefix": best_prefix}

    return {"found": False}


def check_in_startup_log(log_file, endpoint, method):
    """在启动日志中搜索 Spring MVC RequestMapping 注册记录。"""
    if not log_file or not Path(log_file).is_file():
        return {"found": False, "reason": "log_file_not_available"}

    escaped = re.escape(endpoint)
    patterns = [
        re.compile(rf"Mapped\s.*{escaped}"),
        re.compile(rf"RequestMappingHandlerMapping.*{escaped}"),
        re.compile(rf"\{{\[{escaped}"),
    ]

    try:
        with open(log_file, "r", errors="replace") as f:
            for line in f:
                for pat in patterns:
                    if pat.search(line):
                        return {
                            "found": True,
                            "matched_line": line.strip()[:200],
                        }
    except OSError:
        return {"found": False, "reason": "log_file_read_error"}

    return {"found": False}


def probe_endpoint_directly(port, endpoint, method, timeout):
    """直接向目标接口发请求探测。

    当 Swagger 在当前 profile 下关闭时，这是唯一能确认接口存在的方式。
    只要服务返回了 HTTP 响应（非连接失败），就说明接口路由存在。
    404 才是"接口不存在"的信号。
    """
    url = f"http://localhost:{port}{endpoint}"
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-X", method.upper(),
             "-H", "Content-Type: application/json",
             "--connect-timeout", str(timeout),
             "--max-time", str(timeout),
             url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        status_code = result.stdout.strip()
        if not status_code.isdigit():
            return {"found": False, "reason": "invalid_response"}

        code = int(status_code)
        # 000 = 连接失败，404 = 路由不存在
        if code == 0 or code == 404:
            return {"found": False, "http_status": code}

        # 其他任何状态码（200, 400, 401, 405, 500...）都说明路由存在
        return {"found": True, "http_status": code}

    except (subprocess.TimeoutExpired, OSError):
        return {"found": False, "reason": "probe_failed"}


def main():
    parser = argparse.ArgumentParser(description="检查目标接口是否已在运行中的服务中注册")
    parser.add_argument("--port", type=int, required=True, help="服务端口")
    parser.add_argument("--endpoint", required=True, help="目标接口路径，如 /v1/aiAssistant/aiCustomChatFlow")
    parser.add_argument("--method", required=True, help="HTTP 方法，如 POST")
    parser.add_argument("--log-file", help="启动日志文件路径（可选）")
    parser.add_argument("--api-docs-path", default="/v2/api-docs", help="swagger 路径")
    parser.add_argument("--timeout", type=int, default=10, help="请求超时秒数")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    result = {
        "endpoint": args.endpoint,
        "method": args.method,
        "port": args.port,
        "found": False,
        "source": None,
        "match": None,
        "api_docs_reachable": False,
        "log_file_checked": False,
        "direct_probe": False,
    }

    # 优先级 1: /v2/api-docs
    swagger, reachable = fetch_api_docs(args.port, args.api_docs_path, args.timeout)
    result["api_docs_reachable"] = reachable

    if swagger:
        docs_result = check_in_api_docs(swagger, args.endpoint, args.method)
        if docs_result.get("found"):
            result["found"] = True
            result["source"] = "api-docs"
            result["match"] = docs_result.get("match")
            if "matched_prefix" in docs_result:
                result["matched_prefix"] = docs_result["matched_prefix"]
            _emit(result, args.json_output)
            sys.exit(0)

    # 优先级 2: 启动日志
    if args.log_file:
        result["log_file_checked"] = True
        log_result = check_in_startup_log(args.log_file, args.endpoint, args.method)
        if log_result.get("found"):
            result["found"] = True
            result["source"] = "startup_log"
            result["match"] = "log_pattern"
            result["matched_line"] = log_result.get("matched_line")
            _emit(result, args.json_output)
            sys.exit(0)

    # 优先级 3: 业务接口直探（Swagger 可能在当前 profile 下关闭）
    result["direct_probe"] = True
    probe_result = probe_endpoint_directly(args.port, args.endpoint, args.method, args.timeout)
    if probe_result.get("found"):
        result["found"] = True
        result["source"] = "direct_probe"
        result["match"] = "http_alive"
        result["probe_http_status"] = probe_result.get("http_status")
        _emit(result, args.json_output)
        sys.exit(0)

    # 未找到
    if "http_status" in probe_result:
        result["probe_http_status"] = probe_result["http_status"]
    _emit(result, args.json_output)
    if not reachable and not args.log_file:
        sys.exit(3)
    sys.exit(1)


def _emit(data, as_json):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if data["found"]:
            print(f"[found] {data['endpoint']} ({data['method']}) via {data['source']} ({data['match']})")
        else:
            sources = []
            if data["api_docs_reachable"]:
                sources.append("api-docs")
            if data["log_file_checked"]:
                sources.append("startup_log")
            if data.get("direct_probe"):
                sources.append("direct_probe")
            print(f"[not_found] {data['endpoint']} ({data['method']}) — 已检查: {', '.join(sources) or '无可用源'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""HTTP 请求执行器：支持 JSON / multipart / SSE，输出结构化校验结果。

退出码: 0=pass, 1=fail, 2=参数错误, 3=连接失败
"""
import argparse
import json
import sys
import time
import subprocess


def _curl_common(args):
    """构建 curl 通用参数。"""
    cmd = ["curl", "-s", "-S", "-w", "\n%{http_code}\n%{time_total}"]
    cmd.extend(["--connect-timeout", str(min(args.timeout, 10))])
    cmd.extend(["--max-time", str(args.timeout)])
    if args.headers:
        headers = json.loads(args.headers) if isinstance(args.headers, str) else args.headers
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    return cmd


def execute_normal(args):
    """普通 JSON / multipart 请求。"""
    cmd = _curl_common(args)
    cmd.extend(["-X", args.method.upper()])

    if args.files:
        file_list = json.loads(args.files) if isinstance(args.files, str) else args.files
        for f in file_list:
            cmd.extend(["-F", f"{f['field']}=@{f['path']}"])
        if args.body:
            body = json.loads(args.body) if isinstance(args.body, str) else args.body
            for key, value in body.items():
                cmd.extend(["-F", f"{key}={value}"])
    elif args.body or args.body_file:
        content_type = args.content_type or "application/json"
        cmd.extend(["-H", f"Content-Type: {content_type}"])
        if args.body_file:
            cmd.extend(["-d", f"@{args.body_file}"])
        else:
            cmd.extend(["-d", args.body])

    cmd.append(args.url)

    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout + 10)
    except subprocess.TimeoutExpired:
        return {
            "verdict": "fail",
            "failure_category": "request_timeout",
            "status_code": 0,
            "response_time_ms": int((time.time() - start) * 1000),
            "response_body_preview": "",
            "error": "curl 超时",
        }
    except OSError as exc:
        return {
            "verdict": "fail",
            "failure_category": "connection_failed",
            "status_code": 0,
            "response_time_ms": int((time.time() - start) * 1000),
            "response_body_preview": "",
            "error": str(exc),
        }

    output = result.stdout.rstrip("\n")
    lines = output.rsplit("\n", 2)
    if len(lines) >= 3:
        body_text = "\n".join(lines[:-2])
        status_code = int(lines[-2]) if lines[-2].isdigit() else 0
        elapsed_s = float(lines[-1]) if lines[-1].replace(".", "").isdigit() else 0
    elif len(lines) == 2:
        body_text = ""
        status_code = int(lines[0]) if lines[0].isdigit() else 0
        elapsed_s = float(lines[1]) if lines[1].replace(".", "").isdigit() else 0
    else:
        body_text = output
        status_code = 0
        elapsed_s = time.time() - start

    return {
        "status_code": status_code,
        "response_time_ms": int(elapsed_s * 1000),
        "response_body_preview": body_text[:2000],
        "curl_stderr": result.stderr.strip()[:500] if result.stderr else None,
    }


def execute_sse(args):
    """SSE 流式请求：等待首个有效业务事件。"""
    cmd = _curl_common(args)
    cmd.extend(["-X", args.method.upper()])
    cmd.extend(["-H", "Accept: text/event-stream"])
    cmd.extend(["--max-time", str(args.sse_timeout)])

    if args.body:
        content_type = args.content_type or "application/json"
        cmd.extend(["-H", f"Content-Type: {content_type}"])
        cmd.extend(["-d", args.body])
    elif args.body_file:
        content_type = args.content_type or "application/json"
        cmd.extend(["-H", f"Content-Type: {content_type}"])
        cmd.extend(["-d", f"@{args.body_file}"])

    cmd.extend(["-N", args.url])

    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=args.sse_timeout + 10)
    except subprocess.TimeoutExpired:
        return {
            "verdict": "fail",
            "failure_category": "request_timeout",
            "status_code": 0,
            "response_time_ms": int((time.time() - start) * 1000),
            "sse_events_captured": 0,
            "response_body_preview": "",
        }

    output = result.stdout or ""
    elapsed_ms = int((time.time() - start) * 1000)

    # _curl_common 已经加了 -w "\n%{http_code}\n%{time_total}"，从末尾提取真实状态码
    raw_lines = output.rstrip("\n").rsplit("\n", 2)
    if len(raw_lines) >= 3:
        body_text = "\n".join(raw_lines[:-2])
        status_code = int(raw_lines[-2]) if raw_lines[-2].isdigit() else 0
    elif len(raw_lines) == 2:
        body_text = ""
        status_code = int(raw_lines[0]) if raw_lines[0].isdigit() else 0
    else:
        body_text = output
        status_code = 0

    # 解析 SSE 事件
    events = []
    current_event = {}
    for line in body_text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            current_event["data"] = line[5:].strip()
        elif line.startswith("event:"):
            current_event["event"] = line[6:].strip()
        elif line.startswith("id:"):
            current_event["id"] = line[3:].strip()
        elif line == "" and current_event:
            events.append(current_event)
            current_event = {}
    if current_event:
        events.append(current_event)

    first_data_event = None
    for evt in events:
        data = evt.get("data", "")
        if data and data not in ("", "[DONE]", "ping", "heartbeat"):
            first_data_event = evt
            break

    return {
        "status_code": status_code,
        "response_time_ms": elapsed_ms,
        "response_body_preview": body_text[:2000],
        "sse_events_captured": len(events),
        "sse_first_data_event": first_data_event,
    }


def classify_failure(status_code, body_preview):
    """根据 HTTP 状态码和响应体分类失败原因。"""
    if status_code == 404:
        return "http_failed_404_possible_stale_process"
    if status_code in (401, 403) or "token" in (body_preview or "").lower():
        return "http_failed_auth"
    if status_code >= 500:
        return "http_failed_server_error"
    if status_code == 0:
        return "connection_failed"
    return "http_failed"


# 内置 SSE 业务失败关键词：覆盖常见 Spring/Redis/DB 错误与中文业务提示
_SSE_BUILTIN_FAIL_KEYWORDS = [
    "error", "exception", "失败", "错误", "Connection refused",
    "Redis", "connect timed out", "Internal Server Error",
    "NullPointerException", "ClassCastException",
    "SocketTimeoutException", "ConnectException",
]


def check_sse_business_failure(resp, extra_keywords):
    """检查 SSE 首个数据事件是否包含业务级失败信号。

    即使 HTTP 200，如果 SSE data 内容含错误关键词，也应判定失败。
    返回 (is_fail, matched_keyword, detail)。
    """
    first_event = resp.get("sse_first_data_event")
    if not first_event:
        return False, None, None

    data_text = first_event.get("data", "")
    if not data_text:
        return False, None, None

    # 尝试解析为 JSON，提取 message/error/msg 字段一并检查
    check_texts = [data_text]
    try:
        parsed = json.loads(data_text)
        if isinstance(parsed, dict):
            for key in ("message", "error", "msg", "errMsg", "errorMessage"):
                val = parsed.get(key)
                if val and isinstance(val, str):
                    check_texts.append(val)
    except (json.JSONDecodeError, TypeError):
        pass

    keywords = list(_SSE_BUILTIN_FAIL_KEYWORDS)
    if extra_keywords:
        if isinstance(extra_keywords, str):
            extra_keywords = json.loads(extra_keywords)
        keywords.extend(extra_keywords)

    combined = " ".join(check_texts).lower()
    for kw in keywords:
        if kw.lower() in combined:
            return True, kw, data_text[:300]

    return False, None, None


def run_checks(resp, args):
    """对响应执行结构化校验。"""
    checks = {}
    body = resp.get("response_body_preview", "")

    checks["status_code_match"] = resp.get("status_code") == args.expected_status

    if args.must_contain:
        keywords = json.loads(args.must_contain) if isinstance(args.must_contain, str) else args.must_contain
        checks["must_contain_pass"] = all(kw in body for kw in keywords)
    else:
        checks["must_contain_pass"] = True

    if args.must_not_contain:
        keywords = json.loads(args.must_not_contain) if isinstance(args.must_not_contain, str) else args.must_not_contain
        checks["must_not_contain_pass"] = all(kw not in body for kw in keywords)
    else:
        checks["must_not_contain_pass"] = True

    verdict = "pass" if all(checks.values()) else "fail"
    return verdict, checks


def main():
    parser = argparse.ArgumentParser(description="执行 HTTP 请求并输出结构化校验结果")
    parser.add_argument("--url", required=True, help="完整请求 URL")
    parser.add_argument("--method", required=True, help="HTTP 方法")
    parser.add_argument("--headers", help="JSON 对象格式的请求头")
    parser.add_argument("--body", help="JSON 请求体字符串")
    parser.add_argument("--body-file", help="从文件读取请求体")
    parser.add_argument("--files", help="multipart 文件列表 JSON")
    parser.add_argument("--content-type", help="Content-Type，默认 application/json")
    parser.add_argument("--timeout", type=int, default=60, help="普通请求超时秒数")
    parser.add_argument("--sse", action="store_true", help="SSE 模式")
    parser.add_argument("--sse-timeout", type=int, default=30, help="SSE 首个有效事件超时")
    parser.add_argument("--expected-status", type=int, default=200, help="预期 HTTP 状态码")
    parser.add_argument("--must-contain", help="响应体必须包含的关键词 JSON 数组")
    parser.add_argument("--must-not-contain", help="响应体不能包含的关键词 JSON 数组")
    parser.add_argument("--sse-fail-keywords", help="SSE 业务失败关键词 JSON 数组（额外追加到内置列表）")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.sse:
        resp = execute_sse(args)
    else:
        resp = execute_normal(args)

    verdict, checks = run_checks(resp, args)

    result = {
        "verdict": verdict,
        "url": args.url,
        "method": args.method,
        "status_code": resp.get("status_code", 0),
        "expected_status_code": args.expected_status,
        "response_time_ms": resp.get("response_time_ms", 0),
        "response_body_preview": resp.get("response_body_preview", ""),
        "checks": checks,
    }

    if args.sse:
        result["sse_events_captured"] = resp.get("sse_events_captured", 0)
        result["sse_first_data_event"] = resp.get("sse_first_data_event")

        # SSE 业务级失败检测：HTTP 200 但内容含错误信号
        if verdict == "pass":
            is_biz_fail, matched_kw, detail = check_sse_business_failure(
                resp, args.sse_fail_keywords
            )
            if is_biz_fail:
                verdict = "fail"
                result["verdict"] = "fail"
                result["failure_category"] = "sse_business_error"
                result["sse_fail_keyword_matched"] = matched_kw
                result["sse_fail_detail"] = detail

    if resp.get("curl_stderr"):
        result["curl_stderr"] = resp["curl_stderr"]

    if verdict == "fail" and "failure_category" not in result:
        result["failure_category"] = resp.get("failure_category") or classify_failure(
            resp.get("status_code", 0), resp.get("response_body_preview", "")
        )

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if verdict == "pass":
            print(f"[pass] {args.method} {args.url} → {resp.get('status_code')} ({resp.get('response_time_ms')}ms)")
        else:
            cat = result.get("failure_category", "unknown")
            print(f"[fail] {args.method} {args.url} → {resp.get('status_code')} ({cat})")
            print(f"  响应预览: {resp.get('response_body_preview', '')[:200]}")

    sys.exit(0 if verdict == "pass" else 1)


if __name__ == "__main__":
    main()

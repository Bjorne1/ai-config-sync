#!/usr/bin/env python3
"""日志标记扫描：从日志末尾搜索 expected_log_markers。

退出码: 0=全部找到, 1=有缺失, 2=参数错误, 3=日志文件不可读
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def tail_lines(file_path, n):
    """从文件末尾读取 n 行（避免扫描巨大日志）。"""
    path = Path(file_path)
    if not path.is_file():
        return None
    try:
        with path.open("r", errors="replace") as f:
            # 对于中等大小的日志，直接 readlines 比 seek 更简单可靠
            all_lines = f.readlines()
            return all_lines[-n:] if len(all_lines) > n else all_lines
    except OSError:
        return None


def filter_since(lines, since_timestamp):
    """只保留时间戳晚于 since_timestamp 的行。

    假设日志格式以 ISO 或 yyyy-MM-dd HH:mm:ss 开头。
    """
    filtered = []
    found_start = False
    for line in lines:
        if found_start:
            filtered.append(line)
            continue
        # 尝试提取行首时间戳（常见 Spring Boot 格式）
        line_stripped = line.strip()
        if len(line_stripped) >= 19:
            ts_candidate = line_stripped[:19]
            if ts_candidate >= since_timestamp[:19]:
                found_start = True
                filtered.append(line)
    return filtered


def scan_markers(lines, markers):
    """扫描每个 marker 是否出现在日志行中。"""
    results = []
    for marker in markers:
        found = False
        matched_line = None
        for line in lines:
            if marker in line:
                found = True
                matched_line = line.strip()[:200]
                break
        results.append({
            "marker": marker,
            "found": found,
            "matched_line": matched_line,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="扫描日志中的关键标记")
    parser.add_argument("--log-file", required=True, help="日志文件路径")
    parser.add_argument("--markers", required=True, help="JSON 数组格式的标记列表")
    parser.add_argument("--service", default="", help="服务名（用于输出）")
    parser.add_argument("--since-timestamp", help="只扫描此时间戳之后的日志行 (ISO 或 yyyy-MM-dd HH:mm:ss)")
    parser.add_argument("--since-minutes", type=int, help="只扫描最近 N 分钟内的日志行（与 --since-timestamp 互斥，优先级更高）")
    parser.add_argument("--tail-lines", type=int, default=2000, dest="tail_n", help="从末尾读取的最大行数")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    try:
        markers = json.loads(args.markers)
        if not isinstance(markers, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        sys.stderr.write("错误: --markers 必须是 JSON 数组\n")
        sys.exit(2)

    if not markers:
        sys.stderr.write("错误: markers 不能为空\n")
        sys.exit(2)

    lines = tail_lines(args.log_file, args.tail_n)
    if lines is None:
        result = {
            "verdict": "fail",
            "service": args.service,
            "log_file": args.log_file,
            "error": "日志文件不可读",
            "lines_scanned": 0,
            "markers_total": len(markers),
            "markers_found": 0,
            "markers_missing": markers,
            "details": [],
        }
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[fail] 日志文件不可读: {args.log_file}")
        sys.exit(3)

    # --since-minutes 优先于 --since-timestamp
    since_ts = args.since_timestamp
    if args.since_minutes:
        cutoff = datetime.now() - timedelta(minutes=args.since_minutes)
        since_ts = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    if since_ts:
        lines = filter_since(lines, since_ts)

    details = scan_markers(lines, markers)
    found_count = sum(1 for d in details if d["found"])
    missing = [d["marker"] for d in details if not d["found"]]
    verdict = "pass" if found_count == len(markers) else "fail"

    result = {
        "verdict": verdict,
        "service": args.service,
        "log_file": args.log_file,
        "since_timestamp": since_ts,
        "lines_scanned": len(lines),
        "markers_total": len(markers),
        "markers_found": found_count,
        "markers_missing": missing,
        "details": details,
    }

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if verdict == "pass":
            print(f"[pass] {found_count}/{len(markers)} 标记全部找到")
        else:
            print(f"[fail] {found_count}/{len(markers)} 标记找到，缺失: {', '.join(missing)}")
        for d in details:
            status = "✓" if d["found"] else "✗"
            print(f"  {status} {d['marker']}")
            if d["matched_line"]:
                print(f"    → {d['matched_line']}")

    sys.exit(0 if verdict == "pass" else 1)


if __name__ == "__main__":
    main()

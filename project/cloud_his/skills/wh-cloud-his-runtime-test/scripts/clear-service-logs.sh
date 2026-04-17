#!/usr/bin/env bash
set -euo pipefail

# 清空服务日志文件：截断当前日志，保留文件句柄不中断正在运行的服务写入。
# 退出码: 0=成功, 1=部分失败, 2=参数错误

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../" && pwd)"

SERVICE=""
MODULE_PATH=""
LOG_DIR=""
JSON_OUTPUT=0
CLEARED=()
SKIPPED=()

usage() {
  cat <<'EOF'
用法: clear-service-logs.sh --service <name> [选项]

清空服务日志文件（截断而非删除，不中断正在运行的进程写入）。

参数:
  --service       服务名 (必填，用于定位 wh-modules/<name>/logs/)
  --module-path   服务模块路径 (可选，覆盖默认 wh-modules/<service>)
  --log-dir       日志目录 (可选，覆盖自动推导)
  --json          输出 JSON
EOF
}

while (($# > 0)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --service) SERVICE="${2:-}"; shift 2 ;;
    --module-path) MODULE_PATH="${2:-}"; shift 2 ;;
    --log-dir) LOG_DIR="${2:-}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SERVICE" ]]; then
  echo "错误: --service 是必填参数" >&2
  exit 2
fi

# 推导日志目录
if [[ -z "$LOG_DIR" ]]; then
  if [[ -n "$MODULE_PATH" ]]; then
    if [[ "$MODULE_PATH" = /* ]]; then
      LOG_DIR="$MODULE_PATH/logs"
    else
      LOG_DIR="$REPO_ROOT/$MODULE_PATH/logs"
    fi
  else
    LOG_DIR="$REPO_ROOT/wh-modules/$SERVICE/logs"
  fi
fi

if [[ ! -d "$LOG_DIR" ]]; then
  # 日志目录不存在不算失败——可能服务还没启动过
  if [[ "$JSON_OUTPUT" -eq 1 ]]; then
    python3 - "$SERVICE" "$LOG_DIR" <<'PYEOF'
import json, sys
print(json.dumps({
    "service": sys.argv[1],
    "log_dir": sys.argv[2],
    "verdict": "no_log_dir",
    "cleared": [],
    "skipped": [],
}, ensure_ascii=False, indent=2))
PYEOF
  else
    echo "[skip] 日志目录不存在: $LOG_DIR"
  fi
  exit 0
fi

# 清空当前日志文件（*.log），不删文件、不动 history/ 归档
for logfile in "$LOG_DIR"/*.log; do
  [[ -f "$logfile" ]] || continue
  if : > "$logfile" 2>/dev/null; then
    CLEARED+=("$(basename "$logfile")")
  else
    SKIPPED+=("$(basename "$logfile")")
  fi
done

# 输出
CLEARED_JSON=$(printf '%s\n' "${CLEARED[@]}" 2>/dev/null | python3 -c "import sys,json;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")
SKIPPED_JSON=$(printf '%s\n' "${SKIPPED[@]}" 2>/dev/null | python3 -c "import sys,json;print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")

VERDICT="ok"
if [[ ${#SKIPPED[@]} -gt 0 ]]; then
  VERDICT="partial"
fi
if [[ ${#CLEARED[@]} -eq 0 && ${#SKIPPED[@]} -eq 0 ]]; then
  VERDICT="no_logs"
fi

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  python3 - "$SERVICE" "$LOG_DIR" "$VERDICT" "$CLEARED_JSON" "$SKIPPED_JSON" <<'PYEOF'
import json, sys
service, log_dir, verdict, cleared_j, skipped_j = sys.argv[1:6]
print(json.dumps({
    "service": service,
    "log_dir": log_dir,
    "verdict": verdict,
    "cleared": json.loads(cleared_j),
    "skipped": json.loads(skipped_j),
}, ensure_ascii=False, indent=2))
PYEOF
else
  echo "[$VERDICT] $SERVICE 日志已清空 ($LOG_DIR)"
  for f in "${CLEARED[@]}"; do
    echo "  ✓ $f"
  done
  for f in "${SKIPPED[@]}"; do
    echo "  ✗ $f (无权限)"
  done
fi

if [[ "$VERDICT" == "partial" ]]; then
  exit 1
fi
exit 0

#!/usr/bin/env bash
set -euo pipefail

# 服务就绪检查：轮询端口 + 健康检查 + 接口存在性，直到就绪或超时
# 退出码: 0=ready, 1=timeout, 2=参数错误

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PORT=""
ENDPOINT=""
METHOD=""
TIMEOUT=300
INTERVAL=5
LOG_FILE=""
JSON_OUTPUT=0

usage() {
  cat <<'EOF'
用法: check-service-ready.sh --port <port> [选项]

轮询检查服务是否就绪：端口监听 → HTTP 健康 → 接口已加载。

参数:
  --port         服务端口 (必填)
  --endpoint     目标接口路径 (可选，有则额外验证接口已注册)
  --method       HTTP 方法，搭配 --endpoint
  --timeout      最大等待秒数，默认 300
  --interval     轮询间隔秒数，默认 5
  --log-file     启动日志路径 (可选)
  --json         输出 JSON 格式
EOF
}

while (($# > 0)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --endpoint) ENDPOINT="${2:-}"; shift 2 ;;
    --method) METHOD="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --interval) INTERVAL="${2:-}"; shift 2 ;;
    --log-file) LOG_FILE="${2:-}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$PORT" ]]; then
  echo "错误: --port 是必填参数" >&2
  exit 2
fi

START_TIME=$SECONDS
DEADLINE=$((SECONDS + TIMEOUT))

PORT_LISTENING="false"
HEALTH_CHECK="not_checked"
ENDPOINT_LOADED="not_checked"

emit_result() {
  local ready="$1"
  local elapsed=$((SECONDS - START_TIME))

  if [[ "$JSON_OUTPUT" -eq 1 ]]; then
    python3 - "$ready" "$PORT" "$PORT_LISTENING" "$HEALTH_CHECK" "$ENDPOINT_LOADED" "$elapsed" "$TIMEOUT" <<'PYEOF'
import json, sys
args = sys.argv[1:]
ready, port, port_listening, health_check, endpoint_loaded, elapsed, timeout = args
print(json.dumps({
    "ready": ready == "true",
    "port": int(port),
    "port_listening": port_listening == "true",
    "health_check": health_check,
    "endpoint_loaded": endpoint_loaded,
    "elapsed_seconds": int(elapsed),
    "timeout_seconds": int(timeout),
}, ensure_ascii=False, indent=2))
PYEOF
  else
    if [[ "$ready" == "true" ]]; then
      echo "[ready] 端口 $PORT 就绪 (${elapsed}s)"
    else
      echo "[timeout] 端口 $PORT 未就绪 (${elapsed}s/${TIMEOUT}s)"
    fi
    echo "  端口监听: $PORT_LISTENING"
    echo "  健康检查: $HEALTH_CHECK"
    echo "  接口加载: $ENDPOINT_LOADED"
  fi
}

while ((SECONDS < DEADLINE)); do
  # Step 1: 端口监听检查
  if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    PORT_LISTENING="true"
  else
    PORT_LISTENING="false"
    sleep "$INTERVAL"
    continue
  fi

  # Step 2: HTTP 健康检查（多级回退：actuator → api-docs → 任意非000响应）
  HTTP_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
    "http://localhost:${PORT}/actuator/health" \
    --connect-timeout 3 2>/dev/null || echo "000")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    HEALTH_CHECK="ok"
  else
    # 回退 1: 尝试 api-docs
    HTTP_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
      "http://localhost:${PORT}/v2/api-docs" \
      --connect-timeout 3 2>/dev/null || echo "000")
    if [[ "$HTTP_STATUS" == "200" ]]; then
      HEALTH_CHECK="ok_via_api_docs"
    else
      # 回退 2: 直接探测根路径，只要有 HTTP 响应就算服务活着
      ROOT_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
        "http://localhost:${PORT}/" \
        --connect-timeout 3 2>/dev/null || echo "000")
      if [[ "$ROOT_STATUS" != "000" ]]; then
        HEALTH_CHECK="ok_via_root"
      else
        HEALTH_CHECK="not_ready"
        sleep "$INTERVAL"
        continue
      fi
    fi
  fi

  # Step 3: 接口存在性检查（可选）
  if [[ -n "$ENDPOINT" ]]; then
    EP_ARGS=("--port" "$PORT" "--endpoint" "$ENDPOINT" "--json")
    [[ -n "$METHOD" ]] && EP_ARGS+=("--method" "$METHOD")
    [[ -n "$LOG_FILE" ]] && EP_ARGS+=("--log-file" "$LOG_FILE")

    EP_RESULT=$(python3 "$SCRIPT_DIR/check-endpoint-exists.py" "${EP_ARGS[@]}" 2>/dev/null) || true

    EP_FOUND=$(echo "$EP_RESULT" | python3 -c "
import sys, json
try:
    print('true' if json.load(sys.stdin).get('found') else 'false')
except:
    print('false')
" 2>/dev/null || echo "false")

    if [[ "$EP_FOUND" == "true" ]]; then
      ENDPOINT_LOADED="loaded"
    else
      ENDPOINT_LOADED="not_loaded"
      sleep "$INTERVAL"
      continue
    fi
  fi

  # 全部通过
  emit_result "true"
  exit 0
done

# 超时
emit_result "false"
exit 1

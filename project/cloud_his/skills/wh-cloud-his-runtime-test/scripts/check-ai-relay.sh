#!/usr/bin/env bash
set -euo pipefail

# emr→ai 本机转发口径可达性检查
# 当 emr-service 的 /v1/aiAssistant/* 接口需要联动 ai-service 时，
# 实际走的是 localhost:19087/ai 而非注册中心直连。
#
# 探测策略（按优先级）：
#   1. /v2/api-docs（Swagger 开启时最可靠）
#   2. 业务接口探测（Swagger 在 emr profile 下关闭时的回退）
#
# 退出码: 0=reachable, 1=not_reachable, 2=参数错误

PORT=19087
CONTEXT_PATH="/ai"
PROBE_PATH=""
TIMEOUT=10
JSON_OUTPUT=0

usage() {
  cat <<'EOF'
用法: check-ai-relay.sh [选项]

检查 emr→ai 本机转发口径 (localhost:19087/ai) 是否可达。

参数:
  --port           ai-service 端口，默认 19087
  --context-path   上下文路径，默认 /ai
  --probe-path     业务接口探测路径（api-docs 不可用时的回退）
                   例如 /dify/v1/chatFlow/block
  --timeout        超时秒数，默认 10
  --json           输出 JSON
EOF
}

while (($# > 0)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --port) PORT="${2:-}"; shift 2 ;;
    --context-path) CONTEXT_PATH="${2:-}"; shift 2 ;;
    --probe-path) PROBE_PATH="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

PORT_LISTENING=false
VERDICT="unknown"
PROBE_SOURCE="none"
HTTP_STATUS="000"

# Step 1: 端口监听
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
  PORT_LISTENING=true
else
  VERDICT="port_not_listening"
fi

# Step 2: 探测（多级回退）
if [[ "$PORT_LISTENING" == "true" ]]; then

  # 2a: 尝试 /v2/api-docs
  API_DOCS_URL="http://localhost:${PORT}${CONTEXT_PATH}/v2/api-docs"
  HTTP_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
    "$API_DOCS_URL" --connect-timeout "$TIMEOUT" 2>/dev/null || echo "000")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    VERDICT="reachable"
    PROBE_SOURCE="api_docs"
  else
    # 2b: api-docs 不可用（Swagger 可能在当前 profile 下关闭），尝试业务接口
    if [[ -n "$PROBE_PATH" ]]; then
      PROBE_URL="http://localhost:${PORT}${CONTEXT_PATH}${PROBE_PATH}"
      PROBE_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
        -X POST "$PROBE_URL" \
        -H "Content-Type: application/json" \
        --connect-timeout "$TIMEOUT" 2>/dev/null || echo "000")

      # 业务接口返回非 000（有 HTTP 响应）就算可达
      # 即使返回 400/401/500，说明服务在处理请求，接口存在
      if [[ "$PROBE_STATUS" != "000" ]]; then
        VERDICT="reachable"
        PROBE_SOURCE="business_endpoint"
        HTTP_STATUS="$PROBE_STATUS"
      else
        VERDICT="connection_refused"
      fi
    else
      # 2c: 没有 probe-path，用通用 HEAD 请求探测上下文根路径
      ROOT_STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
        "http://localhost:${PORT}${CONTEXT_PATH}/" \
        --connect-timeout "$TIMEOUT" 2>/dev/null || echo "000")

      if [[ "$ROOT_STATUS" != "000" ]]; then
        VERDICT="reachable"
        PROBE_SOURCE="context_root"
        HTTP_STATUS="$ROOT_STATUS"
      elif [[ "$HTTP_STATUS" == "000" ]]; then
        VERDICT="connection_refused"
      else
        # api-docs 拿到了非 200 的 HTTP 响应，说明服务活着但 Swagger 关了
        VERDICT="reachable"
        PROBE_SOURCE="api_docs_non200_but_alive"
      fi
    fi
  fi
fi

# 输出
PROBE_URL_DISPLAY=""
case "$PROBE_SOURCE" in
  api_docs) PROBE_URL_DISPLAY="$API_DOCS_URL" ;;
  business_endpoint) PROBE_URL_DISPLAY="$PROBE_URL" ;;
  context_root) PROBE_URL_DISPLAY="http://localhost:${PORT}${CONTEXT_PATH}/" ;;
  api_docs_non200_but_alive) PROBE_URL_DISPLAY="$API_DOCS_URL" ;;
  *) PROBE_URL_DISPLAY="http://localhost:${PORT}${CONTEXT_PATH}" ;;
esac

if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  python3 -c "
import json
print(json.dumps({
    'verdict': '$VERDICT',
    'port': $PORT,
    'context_path': '$CONTEXT_PATH',
    'port_listening': $( [[ $PORT_LISTENING == true ]] && echo 'True' || echo 'False' ),
    'probe_source': '$PROBE_SOURCE',
    'probe_url': '$PROBE_URL_DISPLAY',
    'http_status': ${HTTP_STATUS:-0}
}, ensure_ascii=False, indent=2).replace('True','true').replace('False','false'))
"
else
  echo "[$VERDICT] $PROBE_URL_DISPLAY (探测方式: $PROBE_SOURCE, HTTP: $HTTP_STATUS)"
fi

if [[ "$VERDICT" == "reachable" ]]; then
  exit 0
else
  exit 1
fi

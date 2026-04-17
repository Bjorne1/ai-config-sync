#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_SCRIPT="$SCRIPT_DIR/../../wh-drg-mysql/scripts/mysql_query.py"

if [[ ! -f "$BASE_SCRIPT" ]]; then
  echo "未找到底层查询脚本: $BASE_SCRIPT" >&2
  exit 1
fi

export WH_DRG_MYSQL_HOST="${WH_DRG_MYSQL_HOST:-192.168.10.211}"
export WH_DRG_MYSQL_PORT="${WH_DRG_MYSQL_PORT:-3306}"
export WH_DRG_MYSQL_USER="${WH_DRG_MYSQL_USER:-ai_reader}"
export WH_DRG_MYSQL_PASSWORD="${WH_DRG_MYSQL_PASSWORD:-AI_reader2026.}"
export WH_DRG_MYSQL_DATABASE="${WH_DRG_MYSQL_DATABASE:-his}"

if [[ $# -gt 0 && "${1:-}" != -* ]]; then
  case "$1" in
    his|wh_ai|wh_drg|wh_pay)
      export WH_DRG_MYSQL_DATABASE="$1"
      shift
      ;;
    *)
      echo "不支持的数据库: $1" >&2
      echo "仅支持: his wh_ai wh_drg wh_pay" >&2
      exit 2
      ;;
  esac
fi

exec python3 "$BASE_SCRIPT" "$@"

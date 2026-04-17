#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_SCRIPT="$SCRIPT_DIR/mysql_query.py"

if [[ ! -f "$BASE_SCRIPT" ]]; then
  echo "未找到底层查询脚本" >&2
  exit 1
fi

export WH_DRG_MYSQL_HOST="${WH_DRG_MYSQL_HOST:-192.168.10.211}"
export WH_DRG_MYSQL_PORT="${WH_DRG_MYSQL_PORT:-3306}"
export WH_DRG_MYSQL_USER="${WH_DRG_MYSQL_USER:-ai_reader}"
export WH_DRG_MYSQL_PASSWORD="${WH_DRG_MYSQL_PASSWORD:-Ai_reader2026}"
export WH_DRG_MYSQL_DATABASE="${WH_DRG_MYSQL_DATABASE:-his}"

database_arg=""
pass_through=()

while (($# > 0)); do
  case "$1" in
    --database)
      if (($# < 2)); then
        echo "--database 缺少参数" >&2
        exit 2
      fi
      database_arg="$2"
      shift 2
      ;;
    his|wh_ai|wh_drg|wh_pay|wh_report|wh_system)
      if [[ -n "$database_arg" ]]; then
        echo "数据库重复指定" >&2
        exit 2
      fi
      database_arg="$1"
      shift
      ;;
    *)
      pass_through+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$database_arg" ]]; then
  export WH_DRG_MYSQL_DATABASE="$database_arg"
fi

case "$WH_DRG_MYSQL_DATABASE" in
  his|wh_ai|wh_drg|wh_pay|wh_report|wh_system)
    ;;
  *)
    echo "不支持的数据库: $WH_DRG_MYSQL_DATABASE" >&2
    echo "仅支持: his wh_ai wh_drg wh_pay wh_report wh_system" >&2
    exit 2
    ;;
esac

exec python3 "$BASE_SCRIPT" "${pass_through[@]}"

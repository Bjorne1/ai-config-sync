#!/usr/bin/env bash
set -euo pipefail

# 构建产物新鲜度检测：比较 target/ 产物时间 vs src/ 源码时间
# 退出码: 0=fresh, 1=stale/no_artifact, 2=参数错误

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_ROOT/../../.." && pwd)"

MODULE_PATH=""
RUN_MODE="classes"
JSON_OUTPUT=0

usage() {
  cat <<'EOF'
用法: check-build-freshness.sh --module-path <path> [--run-mode classes|jar] [--json]

比较模块的构建产物时间与源码最新修改时间，判断当前产物是否过期。

参数:
  --module-path   模块根目录 (相对于仓库根目录或绝对路径)
  --run-mode      classes (IDE 运行) 或 jar (部署运行)，默认 classes
  --json          输出 JSON 格式
EOF
}

while (($# > 0)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --module-path) MODULE_PATH="${2:-}"; shift 2 ;;
    --run-mode) RUN_MODE="${2:-}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$MODULE_PATH" ]]; then
  echo "错误: --module-path 是必填参数" >&2
  exit 2
fi

if [[ "$RUN_MODE" != "classes" && "$RUN_MODE" != "jar" ]]; then
  echo "错误: --run-mode 必须是 classes 或 jar" >&2
  exit 2
fi

# 解析绝对路径
if [[ "$MODULE_PATH" = /* ]]; then
  ABS_MODULE="$MODULE_PATH"
else
  ABS_MODULE="$REPO_ROOT/$MODULE_PATH"
fi

if [[ ! -d "$ABS_MODULE" ]]; then
  echo "错误: 模块目录不存在: $ABS_MODULE" >&2
  exit 2
fi

# --- 取产物最新时间 ---
ARTIFACT_PATH=""
ARTIFACT_TIME=""
ARTIFACT_FILE=""

if [[ "$RUN_MODE" == "classes" ]]; then
  ARTIFACT_PATH="$ABS_MODULE/target/classes"
  if [[ -d "$ARTIFACT_PATH" ]]; then
    ARTIFACT_LINE=$(find "$ARTIFACT_PATH" -type f ! -name '.gitkeep' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
    if [[ -n "$ARTIFACT_LINE" ]]; then
      ARTIFACT_TIME="${ARTIFACT_LINE%% *}"
      ARTIFACT_FILE="${ARTIFACT_LINE#* }"
    fi
  fi
else
  # jar 模式：先找 target/*.jar
  if [[ -d "$ABS_MODULE/target" ]]; then
    JAR_LINE=$(find "$ABS_MODULE/target" -maxdepth 1 -name '*.jar' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
    if [[ -n "$JAR_LINE" ]]; then
      ARTIFACT_TIME="${JAR_LINE%% *}"
      ARTIFACT_FILE="${JAR_LINE#* }"
      ARTIFACT_PATH="$ABS_MODULE/target"
    fi
  fi
fi

# --- 取源码最新时间 ---
SOURCE_TIME=""
SOURCE_FILE=""

SRC_DIRS=()
[[ -d "$ABS_MODULE/src/main/java" ]] && SRC_DIRS+=("$ABS_MODULE/src/main/java")
[[ -d "$ABS_MODULE/src/main/resources" ]] && SRC_DIRS+=("$ABS_MODULE/src/main/resources")

if [[ ${#SRC_DIRS[@]} -gt 0 ]]; then
  SOURCE_LINE=$(find "${SRC_DIRS[@]}" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
  if [[ -n "$SOURCE_LINE" ]]; then
    SOURCE_TIME="${SOURCE_LINE%% *}"
    SOURCE_FILE="${SOURCE_LINE#* }"
  fi
fi

# --- 判定 ---
VERDICT=""
ACTION=""
MESSAGE=""

if [[ -z "$ARTIFACT_TIME" ]]; then
  VERDICT="no_artifact"
  ACTION="build"
  MESSAGE="未找到构建产物 ($RUN_MODE 模式)"
elif [[ -z "$SOURCE_TIME" ]]; then
  VERDICT="fresh"
  ACTION="none"
  MESSAGE="未找到源码文件，产物视为最新"
else
  # 浮点比较：source > artifact 则 stale
  STALE=$(python3 -c "print('yes' if float('$SOURCE_TIME') > float('$ARTIFACT_TIME') else 'no')" 2>/dev/null || echo "unknown")
  if [[ "$STALE" == "yes" ]]; then
    VERDICT="stale"
    if [[ "$RUN_MODE" == "jar" ]]; then
      ACTION="repackage"
    else
      ACTION="rebuild"
    fi
    # 转换时间戳为可读格式
    ART_ISO=$(python3 -c "from datetime import datetime; print(datetime.fromtimestamp(float('$ARTIFACT_TIME')).strftime('%Y-%m-%d %H:%M:%S'))" 2>/dev/null || echo "$ARTIFACT_TIME")
    SRC_ISO=$(python3 -c "from datetime import datetime; print(datetime.fromtimestamp(float('$SOURCE_TIME')).strftime('%Y-%m-%d %H:%M:%S'))" 2>/dev/null || echo "$SOURCE_TIME")
    MESSAGE="源码 ($SRC_ISO) 晚于产物 ($ART_ISO)，需要重新构建"
  else
    VERDICT="fresh"
    ACTION="none"
    MESSAGE="产物是最新的"
  fi
fi

# --- 输出 ---
if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  python3 -c "
import json
from datetime import datetime

def ts_to_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%dT%H:%M:%S')
    except:
        return None

print(json.dumps({
    'verdict': '$VERDICT',
    'module_path': '$ABS_MODULE',
    'run_mode': '$RUN_MODE',
    'artifact_newest': ts_to_iso('$ARTIFACT_TIME'),
    'artifact_path': $(python3 -c "import json; print(json.dumps('$ARTIFACT_FILE' or None))" 2>/dev/null),
    'source_newest': ts_to_iso('$SOURCE_TIME'),
    'source_path': $(python3 -c "import json; print(json.dumps('$SOURCE_FILE' or None))" 2>/dev/null),
    'action': '$ACTION',
    'message': '$MESSAGE'
}, ensure_ascii=False, indent=2))
"
else
  echo "[$VERDICT] $MESSAGE"
  [[ -n "$ARTIFACT_FILE" ]] && echo "  产物: $ARTIFACT_FILE"
  [[ -n "$SOURCE_FILE" ]] && echo "  源码: $SOURCE_FILE"
  echo "  动作: $ACTION"
fi

if [[ "$VERDICT" == "fresh" ]]; then
  exit 0
else
  exit 1
fi

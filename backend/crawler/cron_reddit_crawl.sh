#!/bin/bash
# Cron wrapper: 每天爬取一个品类的 Reddit 数据（轮转）
# 配合 cron_crawl.sh 的全量爬取使用（cron_crawl 不含 Reddit）
#
# 需要在 Hermes cron 中设置：
#   no_agent=True
#   script=backend/crawler/cron_reddit_crawl.sh
#   schedule: 每天执行一次（和 cron_crawl.sh 错开 2 小时）

set -euo pipefail

# Resolve repo root from script location
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/backend/crawler"

export PYTHONPATH=""
export ENCYCLOPEDIA_API_BASE="${ENCYCLOPEDIA_API_BASE:-http://localhost:8010/api/v1}"
export CRAWLER_USERNAME="${CRAWLER_USERNAME:-admin}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7897}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7897}"

# Read password
PASS_FILE="$REPO_ROOT/backend/.crawler_password"
if [ -f "$PASS_FILE" ]; then
    export CRAWLER_PASSWORD="$(cat "$PASS_FILE")"
elif [ -z "${CRAWLER_PASSWORD:-}" ]; then
    echo "❌ CRAWLER_PASSWORD not set and $PASS_FILE not found"
    exit 1
fi

# 7 个品类轮转：每天爬一个
CATEGORIES=("SEAT_CUSHION" "HEAT_THERAPY" "TENS_THERAPY" "NIGHT_LIGHT" "MEDICATION_MANAGEMENT" "SHOULDER_NECK_HEAT_THERAPY" "FAR_INFRARED")

# 用日期模 7 来确定今天爬哪个品类
DAY_OF_YEAR=$(date +%j)
INDEX=$(( (DAY_OF_YEAR - 1) % 7 ))
CATEGORY="${CATEGORIES[$INDEX]}"

echo "🔥 Reddit 单品类爬取"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "今日品类: $CATEGORY (index=$INDEX)"

VENV_PY="$REPO_ROOT/backend/.venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    VENV_PY="python3"
fi

"$VENV_PY" "$SCRIPTS_DIR/crawl_reddit_single.py" "$CATEGORY" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Reddit 爬取失败 (exit code: $EXIT_CODE)"
    exit $EXIT_CODE
fi

echo ""
echo "✅ Reddit 爬取完成"

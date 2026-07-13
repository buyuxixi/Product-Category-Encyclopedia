#!/bin/bash
# Cron job wrapper — runs the full crawl pipeline without LLM agent.
# Designed for no_agent=True cron mode. Output is delivered verbatim.
#
# Usage in cron: no_agent=True, script=backend/crawler/cron_crawl.sh
set -euo pipefail

# Resolve repo root from script location
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS_DIR="$REPO_ROOT/backend/crawler"

export PYTHONPATH=""
export ENCYCLOPEDIA_API_BASE="${ENCYCLOPEDIA_API_BASE:-http://localhost:8010/api/v1}"
export CRAWLER_USERNAME="${CRAWLER_USERNAME:-admin}"
export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7897}"
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7897}"

# Read password from env or fallback file
if [ -z "${CRAWLER_PASSWORD:-}" ]; then
    PASS_FILE="$REPO_ROOT/backend/.crawler_password"
    if [ -f "$PASS_FILE" ]; then
        export CRAWLER_PASSWORD="$(cat "$PASS_FILE")"
    else
        echo "❌ CRAWLER_PASSWORD not set and $PASS_FILE not found"
        exit 1
    fi
fi

# Health check — just verify the port is responding
if ! curl -sf "$ENCYCLOPEDIA_API_BASE/auth/local/login" -X POST \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"'"$CRAWLER_PASSWORD"'"}' >/dev/null 2>&1; then
    echo "❌ 后端未运行或登录失败 ($ENCYCLOPEDIA_API_BASE 不可达)"
    exit 1
fi

echo "🔥 品类百科 — 每日热点爬取"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "API: $ENCYCLOPEDIA_API_BASE"
echo ""

# Use backend venv python (has httpx, feedparser installed)
VENV_PY="$REPO_ROOT/backend/.venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    VENV_PY="python3"
fi

"$VENV_PY" "$SCRIPTS_DIR/run_full_crawl.py" --save /tmp/crawl_output.json 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ 爬取失败 (exit code: $EXIT_CODE)"
    exit $EXIT_CODE
fi

echo ""
echo "✅ 爬取完成"

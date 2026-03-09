#!/bin/bash
# darts-app の metrics.json を元に、全記事・全チャプターの数値を一括更新する
#
# 使い方: bash scripts/update-numbers.sh
#
# 前提: darts-app 側で npm run metrics を実行済みであること
# metrics.json のパスは環境変数 METRICS_JSON で上書き可能

set -e
cd "$(dirname "$0")/.."

METRICS_JSON="${METRICS_JSON:-../darts-app/docs/metrics.json}"

if [ ! -f "$METRICS_JSON" ]; then
  echo "ERROR: metrics.json not found at $METRICS_JSON"
  echo "Run 'npm run metrics' in darts-app first."
  exit 1
fi

# メトリクス読み取り
LOC=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['loc'])")
COMMITS=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['commits'])")
API_ROUTES=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['apiRoutes'])")
PAGES=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['pages'])")
COMPONENTS=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['components'])")
VERSION=$(python3 -c "import json; print(json.load(open('$METRICS_JSON'))['version'])")

# 丸め値の計算
LOC_ROUNDED=$((LOC / 1000 * 1000))
LOC_DISPLAY=$(printf "%'d" $LOC_ROUNDED)

echo "=== Current metrics ==="
echo "  LOC: ${LOC} (display: ${LOC_DISPLAY}+)"
echo "  Commits: ${COMMITS}"
echo "  API Routes: ${API_ROUTES}"
echo "  Pages: ${PAGES}"
echo "  Components: ${COMPONENTS}"
echo "  Version: ${VERSION}"
echo ""

# 更新対象ファイル一覧
FILES=$(find articles/ books/ -name "*.md" -type f 2>/dev/null)

UPDATED=0

for f in $FILES; do
  CHANGED=false

  # 67,000行 → 最新値（articles のフッターと本文）
  if grep -q "67,000行" "$f" 2>/dev/null; then
    sed -i '' "s/67,000行/${LOC_DISPLAY}行/g" "$f"
    CHANGED=true
  fi

  # 55,000行 → 最新値（Book タイトル内）
  if grep -q "55,000行" "$f" 2>/dev/null; then
    sed -i '' "s/55,000行/${LOC_DISPLAY}行/g" "$f"
    CHANGED=true
  fi

  # 298コミット → 最新値
  if grep -q "298" "$f" 2>/dev/null; then
    sed -i '' "s/298のコミット/${COMMITS}のコミット/g" "$f"
    # テーブル形式: | 298 |
    sed -i '' "s/| 298 |/| ${COMMITS} |/g" "$f"
    CHANGED=true
  fi

  # API Routes: 30本 → 最新値
  if grep -q "30本のAPIルート" "$f" 2>/dev/null; then
    sed -i '' "s/30本のAPIルート/${API_ROUTES}本のAPIルート/g" "$f"
    CHANGED=true
  fi

  # API Routes テーブル: | 40 | → 最新値 (APIの行のみ)
  if grep -q "API Routes" "$f" 2>/dev/null; then
    sed -i '' "s/| API Routes | 40 |/| API Routes | ${API_ROUTES} |/g" "$f"
    CHANGED=true
  fi

  # 40ページ → 最新値
  if grep -q "40ページ" "$f" 2>/dev/null; then
    sed -i '' "s/40ページ/${PAGES}ページ/g" "$f"
    CHANGED=true
  fi

  # コンポーネント: 120 → 最新値
  if grep -q "| 120 |" "$f" 2>/dev/null; then
    sed -i '' "s/| コンポーネント数 | 120 |/| コンポーネント数 | ${COMPONENTS} |/g" "$f"
    CHANGED=true
  fi

  # コンポーネント: 106コンポーネント → 最新値
  if grep -q "106コンポーネント" "$f" 2>/dev/null; then
    sed -i '' "s/106コンポーネント/${COMPONENTS}コンポーネント/g" "$f"
    CHANGED=true
  fi

  if $CHANGED; then
    UPDATED=$((UPDATED + 1))
    echo "  Updated: $f"
  fi
done

echo ""
echo "=== ${UPDATED} files updated ==="
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Sync books:     bash scripts/sync-books.sh"
echo "  3. Commit & push:  git add -A && git commit -m 'docs: メトリクス数値を最新化' && git push"

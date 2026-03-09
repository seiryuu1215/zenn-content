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

# 丸め値の計算（千の位で丸め）
LOC_ROUNDED=$((LOC / 1000 * 1000))
LOC_DISPLAY=$(printf "%'d" $LOC_ROUNDED)

echo "=== Current metrics ==="
echo "  LOC: ${LOC} (display: ${LOC_DISPLAY})"
echo "  Commits: ${COMMITS}"
echo "  API Routes: ${API_ROUTES}"
echo "  Pages: ${PAGES}"
echo "  Components: ${COMPONENTS}"
echo "  Version: ${VERSION}"
echo ""

# 更新対象ファイル一覧（dev-diary は履歴なので本文は除外、タイトルのみ対象）
FILES=$(find articles/ books/ -name "*.md" -type f 2>/dev/null)
YAML_FILES=$(find books/ -name "config.yaml" -type f 2>/dev/null)

UPDATED=0

# LOC の一括置換: [0-9]{2,3},000行 パターンを最新値に
# 例: 82,000行 → 90,000行、67,000行 → 90,000行
for f in $FILES $YAML_FILES; do
  CHANGED=false

  # LOC: X,000行 / X,000+ / X,000行の → 最新値（千の位丸め）
  # dev-diary の本文差分テーブル（→ を含む行）はスキップ
  if grep -q "[0-9][0-9],[0-9][0-9][0-9]行" "$f" 2>/dev/null; then
    # 「→」を含む行はスキップ（差分テーブル）
    sed -i '' "/→/!s/[0-9][0-9],[0-9][0-9][0-9]行/${LOC_DISPLAY}行/g" "$f"
    CHANGED=true
  fi

  # config.yaml の LOC（Book タイトル）
  if echo "$f" | grep -q "config.yaml"; then
    if grep -q "[0-9][0-9],[0-9][0-9][0-9]行" "$f" 2>/dev/null; then
      sed -i '' "s/[0-9][0-9],[0-9][0-9][0-9]行/${LOC_DISPLAY}行/g" "$f"
      CHANGED=true
    fi
  fi

  # コミット数: テーブル形式 | コミット数 | NNN |
  if grep -q "| コミット数 |" "$f" 2>/dev/null; then
    sed -i '' "s/| コミット数 | [0-9]* |/| コミット数 | ${COMMITS}+ |/g" "$f"
    CHANGED=true
  fi

  # API Routes テーブル
  if grep -q "| API Routes |" "$f" 2>/dev/null; then
    sed -i '' "s/| API Routes | [0-9]* |/| API Routes | ${API_ROUTES} |/g" "$f"
    CHANGED=true
  fi

  # ページ数テーブル
  if grep -q "| ページ数 |" "$f" 2>/dev/null; then
    sed -i '' "s/| ページ数 | [0-9]* |/| ページ数 | ${PAGES} |/g" "$f"
    CHANGED=true
  fi

  # コンポーネント数テーブル
  if grep -q "| コンポーネント数 |" "$f" 2>/dev/null; then
    sed -i '' "s/| コンポーネント数 | [0-9]* |/| コンポーネント数 | ${COMPONENTS} |/g" "$f"
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

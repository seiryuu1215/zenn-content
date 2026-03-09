#!/bin/bash
# articles/ の記事を books/ のチャプターとしてコピーする
# シンボリックリンクではなく実ファイルコピーで Zenn 互換性を確保
#
# 使い方: bash scripts/sync-books.sh

set -e
cd "$(dirname "$0")/.."

echo "=== Syncing articles to book chapters ==="

# Book 1: claude-code-darts-lab (追加チャプター5本)
BOOK1_DIR="books/claude-code-darts-lab"
BOOK1_ARTICLES=(
  "darts-lab-dual-auth"
  "darts-lab-stripe-flow"
  "darts-lab-line-statemachine"
  "darts-lab-defense-layers"
  "darts-lab-cron-pipeline"
)

for slug in "${BOOK1_ARTICLES[@]}"; do
  src="articles/${slug}.md"
  dst="${BOOK1_DIR}/${slug}.md"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "  Copied: $src → $dst"
  else
    echo "  WARN: $src not found"
  fi
done

# Book 2: darts-lab-beginners (全8チャプター)
BOOK2_DIR="books/darts-lab-beginners"
BOOK2_ARTICLES=(
  "darts-lab-architecture"
  "darts-lab-requirements"
  "darts-lab-auth"
  "darts-lab-api"
  "darts-lab-firestore"
  "darts-lab-cron-line"
  "darts-lab-stripe"
  "darts-lab-glossary"
)

for slug in "${BOOK2_ARTICLES[@]}"; do
  src="articles/${slug}.md"
  dst="${BOOK2_DIR}/${slug}.md"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "  Copied: $src → $dst"
  else
    echo "  WARN: $src not found"
  fi
done

echo "=== Sync complete ==="

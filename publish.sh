#!/bin/bash
# Zenn公開スクリプト — 実行するだけで記事+書籍が公開される
set -e

cd "$(dirname "$0")"

echo "📕 書籍を公開中..."
sed -i '' 's/published: false/published: true/' books/claude-code-devdex/config.yaml

echo "📝 告知記事を公開中..."
sed -i '' 's/published: false/published: true/' articles/devdex-launch.md

echo "🚀 GitHubにpush..."
git add books/claude-code-devdex/config.yaml articles/devdex-launch.md
git commit -m "feat: Zenn書籍+告知記事を公開"
git push origin main

echo ""
echo "✅ 公開完了！"
echo "📕 書籍: https://zenn.dev/seiryuu/books/claude-code-devdex"
echo "📝 記事: https://zenn.dev/seiryuu/articles/devdex-launch"
echo ""
echo "⏰ Zennのデプロイに数分かかります。5分後に上記URLを確認してください。"

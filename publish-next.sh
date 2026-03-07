#!/bin/bash
# 未公開記事を1本ずつ公開するスクリプト
# 使い方: ./publish-next.sh
# 毎日1回実行して1本ずつ公開する

cd "$(dirname "$0")"

# 公開優先順（ポートフォリオの掲載順）
QUEUE=(
  "darts-lab-dual-auth"
  "darts-lab-stripe-flow"
  "darts-lab-line-statemachine"
  "darts-lab-requirements"
  "darts-lab-stripe"
  "darts-lab-glossary"
  "saas-launcher"
)

published=0
for slug in "${QUEUE[@]}"; do
  file="articles/${slug}.md"
  if [ ! -f "$file" ]; then
    continue
  fi
  if grep -q "^published: false" "$file"; then
    sed -i '' 's/^published: false$/published: true/' "$file"
    echo "公開: $slug"
    git add "$file"
    git commit -m "publish: $(head -2 "$file" | grep '^title:' | sed 's/title: "//' | sed 's/"$//')"
    git push
    published=1
    break
  fi
done

if [ $published -eq 0 ]; then
  echo "未公開の記事はありません"
fi

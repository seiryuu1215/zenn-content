---
description: コミットメッセージ規約。実装完了時に自動適用する。
---

# コミット規約

## 形式

```
type: 日本語の説明
```

## type 一覧

| type | 用途 |
|------|------|
| `docs` | 記事・Book の新規追加・更新 |
| `fix` | 記事の誤字・数値修正 |
| `chore` | スクリプト・設定ファイルの変更 |
| `publish` | 新記事の公開 |

## 例

```
docs: メトリクス数値を最新化
publish: ダークモード実装記事を公開
fix: darts-lab-auth の認証フロー図を修正
chore: sync-books.sh のコピー先を追加
```

## 同期タグ

darts-app の変更に起因する更新には `[sync:darts-app]` タグを付ける。

```
docs: メトリクス数値を最新化 [sync:darts-app]
```

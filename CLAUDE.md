# CLAUDE.md

## プロジェクト概要

Zenn 連携リポジトリ。技術記事と Book を管理する。
GitHub 連携により、main ブランチへの push で Zenn に自動デプロイされる。

## 言語

- 記事本文: 日本語
- Claude Codeとの会話: 日本語で応答してください

## ディレクトリ構成

```
articles/      — 個別の技術記事（.md）
books/         — Book（チャプター構成の長編コンテンツ）
  claude-code-darts-lab/   — Claude Code × darts Lab の開発記録
  darts-lab-beginners/     — IT初心者向け Web アプリ開発解説
scripts/       — 自動化スクリプト
```

## Zenn プラットフォームの制限事項

### 投稿レート制限

- **24時間あたりの公開数に上限あり**（具体的な数は非公開、スパム防止目的）
- 直近24時間の投稿数（予約投稿含む）で判定される
- 上限に達した場合、最後の投稿から24時間経過後に再投稿可能
- 大量投稿（ブログ移行等）が必要な場合は Zenn のお問い合わせフォームから制限緩和を申請できる

### 運用上の注意

- **1日に大量の記事を公開しない** — 3〜5記事/日 を上限の目安にする
- 数値更新のような一括変更は **1回の push でまとめる**（記事ごとの push は避ける）
- GitHub 連携時、Web 上での編集は次回デプロイで上書きされる

## 記事執筆ルール

### ファイル名

- kebab-case: `darts-lab-[topic].md`
- darts Lab 関連: `darts-lab-` プレフィックス
- その他プロダクト: プロダクト名プレフィックス（例: `saas-launcher.md`）

### frontmatter 規約

```yaml
---
title: "日本語タイトル（60字以内推奨）"
emoji: "関連する絵文字1つ"
type: "tech"          # tech（技術記事）または idea（アイデア）
topics: ["nextjs", "typescript", "firebase", "個人開発"]  # 最大5つ
published: true       # false で下書き
---
```

### topics のルール

- 最大5つ
- 小文字英数のみ（Zenn の制約）
- よく使う topics: `nextjs`, `typescript`, `firebase`, `claudecode`, `個人開発`, `react`, `line`
- 日本語 topics は `個人開発` のみ使用可

### 語調

- ですます調
- エンジニア向け（初心者記事は除く）
- コード例は実際の darts-app のコードを使用する

## Book 構成

### Book 1: claude-code-darts-lab

「Claude Codeで82,000行のWebアプリを3ヶ月で作った全記録」
- 10章（書き下ろし） + 5章（articles/ からコピー）
- 対象読者: AI駆動開発に興味があるエンジニア

### Book 2: darts-lab-beginners

「IT初心者でもわかるWebアプリ開発 — darts Labの設計図で学ぶ」
- 8章（全て articles/ からコピー）
- 対象読者: Web 開発初学者

### Book チャプターの管理方法

articles/ が正（Single Source of Truth）。books/ 内のチャプターは **コピー** で管理する。
シンボリックリンクは使わない（Zenn の GitHub 連携で解決されない場合があるため）。

**記事更新時の手順:**
1. articles/ の記事を編集する
2. `bash scripts/sync-books.sh` を実行して books/ にコピーする
3. まとめて commit & push する

### 数値更新の手順

1. darts-app で `npm run metrics` を実行し `docs/metrics.json` を更新
2. zenn-content で `bash scripts/update-numbers.sh` を実行（全記事・全チャプターの数値を一括置換）
3. `bash scripts/sync-books.sh` を実行（articles → books にコピー反映）
4. `git add -A && git commit -m 'docs: メトリクス数値を最新化' && git push`

## クロスリポ同期ルール

このリポジトリの記事は **darts-app** のコード・設計を解説している。
darts-app に以下の変更があった場合、対応する記事の更新が必要。

| darts-app の変更 | 更新が必要な記事 |
|------------------|-----------------|
| 認証フロー変更 | darts-lab-auth.md, darts-lab-dual-auth.md |
| Stripe/決済変更 | darts-lab-stripe.md, darts-lab-stripe-flow.md |
| API 設計変更 | darts-lab-api.md |
| Firestore スキーマ変更 | darts-lab-firestore.md |
| LINE Bot 変更 | darts-lab-cron-line.md, darts-lab-line-statemachine.md |
| Cron/自動化変更 | darts-lab-cron-pipeline.md |
| セキュリティ変更 | darts-lab-defense-layers.md |
| LOC が大きく変動 | Book タイトル（config.yaml の行数表記） |

### 数値の参照元

darts-app の `docs/metrics.json` を正とする。
記事内の「○○行」「○○個のAPI」等の数値はこのファイルと整合させること。

## デプロイ

- main ブランチに push すれば Zenn に自動反映される
- 記事を公開する前に `published: true` になっていることを確認
- Book の公開は config.yaml の `published: true` で制御
- **数値更新は 1 push にまとめる**（レート制限回避のため）

---
title: "67,000行のSaaSから抽出した Next.js + Firebase + Stripe スターターキットを公開した"
emoji: "🚀"
type: "tech"
topics: ["nextjs", "firebase", "stripe", "saas", "typescript"]
published: true
---

## 作ったもの

**SaaS Launcher** — Next.js + Firebase + Stripe の SaaS スターターキット。

https://saas-launcher.vercel.app

自分が運用している 67,000行の SaaS（ダーツスコア管理アプリ）から、認証・決済・セキュリティの共通基盤を抽出して汎用化したものです。

**¥2,980** で販売しています。

👉 [購入はこちら](https://saas-launcher.lemonsqueezy.com/checkout/buy/94832482-9248-42da-b929-2e7fa91a8dd2)

## なぜ作ったか

SaaS を作るとき、毎回同じことでつまずきます。

- Firebase Auth と NextAuth の連携
- Stripe のサブスクリプション（Checkout → Webhook → Firestore 同期）
- ロール別の権限管理（API + UI 両方）
- セキュリティ（CSP、レートリミット、Firestore ルール）

英語圏には ShipFast ($199)、Makerkit ($299) などのスターターキットがありますが、日本語のものは見当たりませんでした。

「自分が1年運用して改善してきたコードを、そのまま渡せばいいのでは？」と思い、汎用化して公開しました。

## 何が入っているか

### 認証（NextAuth + Firebase Auth）

```
app/api/auth/[...nextauth]/route.ts  → NextAuth ハンドラ
lib/auth.ts                          → Firebase REST API でサーバーサイド認証
lib/firebase.ts                      → クライアント SDK（遅延初期化）
lib/firebase-admin.ts                → Admin SDK（Base64 SA 対応）
```

ポイント:
- サーバーサイドでは Firebase Client SDK ではなく **REST API を直接呼ぶ**（Next.js の patched fetch との互換性問題を回避）
- Firebase Admin の認証情報は **Base64 エンコード**で Vercel 環境変数に安全に格納
- JWT コールバックで **Firestore から最新の role を毎回取得**（管理者が権限変更したら即反映）

### 決済（Stripe サブスクリプション）

```
app/api/stripe/checkout/route.ts  → Checkout Session 作成
app/api/stripe/portal/route.ts    → Customer Portal
app/api/stripe/webhook/route.ts   → Webhook 処理（4イベント）
scripts/setup-stripe.mjs          → 商品・価格の自動セットアップ
```

ポイント:
- **冪等性チェック**: Firestore の `stripeEvents` コレクションで Webhook の重複処理を防止
- **プロモ価格対応**: Firestore の `config/pricing` で期間限定割引を管理
- **トライアル期間**: Checkout Session 作成時に `trial_period_days` を自動設定
- **セットアップ自動化**: `node scripts/setup-stripe.mjs` 一発で商品と価格を作成

### API ミドルウェア

```typescript
// lib/api-middleware.ts
export const POST = withErrorHandler(
  withAuth(async (req, { userId, role, email }) => {
    // userId, role, email が保証された状態で処理
  }),
  'エラーラベル',
);
```

4つのデコレータを **関数合成** で重ねる設計:
- `withErrorHandler` — try-catch + Sentry + 500 レスポンス
- `withAuth` — セッション検証 + userId/role/email をコンテキスト注入
- `withAdmin` — admin ロール検証
- `withPermission` — 任意の権限関数でチェック

### セキュリティ

- **CSP ヘッダー**: Firebase, Stripe, Sentry のドメインを許可した Content Security Policy
- **レートリミット**: Upstash Redis（未設定時はインメモリフォールバック）
- **Firestore ルール**: `role`, `stripeCustomerId` 等を **保護フィールド** として Admin SDK からのみ書き込み可能に

```
// firestore.rules（一部抜粋）
match /users/{userId} {
  allow read: if request.auth != null && request.auth.uid == userId;
  allow create: if request.auth != null && request.auth.uid == userId
    && !request.resource.data.keys().hasAny(['role', 'stripeCustomerId', ...]);
  allow update: if request.auth != null && request.auth.uid == userId
    && !request.resource.data.diff(resource.data).affectedKeys().hasAny(['role', ...]);
}
```

### その他

- **PWA**: Serwist で Service Worker 自動生成
- **テスト**: Vitest で 22 テスト（権限・レートリミット・Stripe・ユーティリティ）
- **CI/CD**: GitHub Actions 4段階ゲート（Lint → Format → Test → Build）
- **UI**: shadcn/ui + Tailwind CSS v4

## 技術スタック

| カテゴリ | 技術 |
|----------|------|
| フレームワーク | Next.js 16 (App Router, Turbopack) |
| 認証 | NextAuth v4 + Firebase Auth |
| DB | Cloud Firestore |
| 決済 | Stripe |
| UI | shadcn/ui + Tailwind CSS v4 |
| テスト | Vitest |
| エラー監視 | Sentry |
| PWA | Serwist |
| CI | GitHub Actions |

## セットアップ手順

```bash
# 1. クローン & インストール
git clone <repo> my-saas && cd my-saas && npm install

# 2. 環境変数を設定
cp .env.example .env
# Firebase と Stripe の値を .env に記入

# 3. Stripe 商品を自動作成
node scripts/setup-stripe.mjs

# 4. 起動
npm run dev
```

Firebase の設定（プロジェクト作成、Auth 有効化、Firestore 作成）を済ませれば、**30分以内に認証 → 課金 → ダッシュボードまで動く状態** になります。

## デモ

https://saas-launcher.vercel.app

- LP → ログイン → 登録 → ダッシュボード → 設定 → 料金プラン まで一通り動きます
- Stripe Checkout（テストモード）で決済フローも確認できます

## 実運用で得た知見

このキットのコードは「動くテンプレート」ではなく、**1年間の運用で踏んだ地雷を回避済みのコード** です。

例:
- Firebase Client SDK を Node.js で使うと `auth/invalid-credential` になる → REST API に切り替え
- Vercel 環境変数に JSON を入れると改行文字が壊れる → Base64 エンコード
- Next.js の patched `fetch` が外部 API 呼び出しで挙動が変わる → `node:https` を使用
- Stripe Webhook が重複配信される → Firestore で冪等性チェック
- `useSearchParams` を Suspense なしで使うとビルドエラー → Suspense 境界で対応

これらは全てキット内で対処済みです。

## 価格

**¥2,980**（買い切り）

含まれるもの:
- ソースコード一式（ZIP）
- 日本語 README（セットアップガイド・カスタマイズガイド）
- 商用利用可

👉 [購入はこちら](https://saas-launcher.lemonsqueezy.com/checkout/buy/94832482-9248-42da-b929-2e7fa91a8dd2)

## まとめ

- 67,000行の本番 SaaS から認証・決済・セキュリティを抽出
- 日本語コード・日本語ドキュメント
- 30分で動く状態になる
- 実運用の知見が反映済み
- ¥2,980

SaaS を作りたいけど認証と決済で毎回つまずく方、ぜひ使ってみてください。

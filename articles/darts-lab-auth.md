---
title: "IT初心者でもわかるログインの仕組み — JWTと認証・認可を実例で解説"
emoji: "🔐"
type: "tech"
topics: ["nextauth", "firebase", "jwt", "初心者向け"]
published: true
---

## 「ログインする」って何が起きてるの？

普段何気なくやっている「ログイン」。技術的には何が起きているのか、遊園地のリストバンドに例えて説明しよう。

1. **認証**（Authentication）= 「あなたは誰？」の確認 → チケット売り場で身分証を見せる
2. **認可**（Authorization）= 「あなたは何ができる？」の判定 → リストバンドの色でアトラクション制限

ログイン画面でメールアドレスとパスワードを入力するのが「認証」。ログイン後に「この機能は有料ユーザーだけ」と制限されるのが「認可」だ。

## JWT — 改ざんできないデジタルリストバンド

ログインに成功すると、サーバーから **JWT（JSON Web Token）** というトークン（デジタルリストバンド）が発行される。

JWTには3つの情報が入っている。

| 部分 | 内容 | 例 |
|------|------|----|
| ヘッダー | トークンの種類 | 「これはJWTです」 |
| ペイロード | ユーザー情報 | `userId: "abc123", role: "pro"` |
| 署名 | 改ざん防止 | サーバーだけが持つ秘密鍵で生成 |

このJWTがブラウザのCookieに保存され、以降のリクエストに自動的に添付される。サーバーはJWTの署名を検証するだけで「このリクエストは誰からか」がわかる。

## darts Lab のデュアル認証

darts Lab では **NextAuth.js** と **Firebase Auth** を両方使っている。なぜ2つも必要なのか？

```
ユーザー → Firebase Auth（メール/パスワードで認証）
              ↓
         NextAuth.js（JWTを発行、roleを埋め込み）
              ↓
    ブラウザ: Cookie にJWT保存
    サーバー: JWTからユーザー情報を取得
    Firestore: Firebase Authでアクセス制御
```

| 認証基盤 | 得意なこと |
|----------|-----------|
| **NextAuth.js** | ページのセッション管理。APIで「この人はPROか？」を判定 |
| **Firebase Auth** | Firestoreのセキュリティルール。「自分のデータだけ読める」を実現 |

それぞれ役割が違うから、両方を組み合わせている。

## 3段階のロールシステム

darts Lab のユーザーは3つのロール（役割）に分かれている。

| ロール | できること | なれる条件 |
|--------|-----------|-----------|
| `general` | 基本機能（セッティング登録1件、閲覧、検索） | 無料登録 |
| `pro` | 全機能（DARTSLIVE連携、詳細分析、CSV出力、無制限登録） | 月額サブスク |
| `admin` | pro + 管理者機能（ユーザー管理、記事投稿） | 管理者が設定 |

権限判定は `lib/permissions.ts` という1つのファイルに集約している。

```typescript
// admin は常に pro の上位互換
export function isPro(role) {
  return role === 'pro' || role === 'admin';
}

// 一般ユーザーはセッティング1件まで
export function getSettingsLimit(role) {
  if (isPro(role)) return null; // 無制限
  return 1;
}
```

ポイントは `isPro()` が `admin` でも `true` を返すこと。こうすることで、権限チェックを書くたびに `role === 'pro' || role === 'admin'` と毎回書く必要がなくなる。

## APIミドルウェア — 自動的に認証チェック

すべてのAPIルートに手動で認証チェックを書くのは大変だ。そこで **ミドルウェア**（処理の前に自動で実行されるチェック機能）を用意した。

```typescript
// ログインチェックだけ
export const POST = withAuth(handler);

// 管理者限定（Firestoreからroleを再確認）
export const POST = withAdmin(handler);

// 特定の権限が必要
export const POST = withPermission(canUseDartslive, 'PRO限定です', handler);
```

`withAdmin` は JWT の role だけでなく、**Firestoreから直接roleを再取得して二重確認** する。JWTは改ざんリスクがゼロではないため、管理者操作だけは特に慎重にチェックしている。

## まとめ

- 認証 =「あなたは誰？」、認可 =「あなたは何ができる？」
- JWT は改ざんできないデジタルリストバンド
- darts Lab は NextAuth.js + Firebase Auth のデュアル構成
- 3段階ロール（general / pro / admin）で機能を制御
- ミドルウェアで認証チェックを自動化

次の記事では、サブスク決済（Stripe）が裏側でどう動いているかを解説する。

---

*この記事は darts Lab（67,000行のダーツスタッツ管理アプリ）の実装を元に解説しています。*

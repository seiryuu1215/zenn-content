---
title: "デモアカウント設計パターン — useDemoGuard・JWTクレーム・日次リセットの実装"
emoji: "🎭"
type: "tech"
topics: ["nextjs", "firebase", "typescript", "個人開発"]
published: true
---

## はじめに

個人開発のWebアプリを公開するとき、**デモアカウント**があると採用担当者やユーザーに機能を体験してもらいやすくなります。

しかし、デモアカウントの設計は意外と奥が深いです。

- 書き込み操作をどう制限するか？
- デモデータが壊れたらどうリセットするか？
- 認証フローにどう統合するか？

この記事では、ダーツプレイヤー向けWebアプリ **darts Lab** で実装したデモアカウント設計パターンを解説します。

## アーキテクチャ概要

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  フロント     │    │   API層       │    │  Cron Job   │
│  useDemoGuard│───▶│  withAuth    │    │  日次リセット │
│  （UI制限）   │    │  （API制限）   │    │  （データ復元）│
└─────────────┘    └──────────────┘    └─────────────┘
```

3層の防御でデモアカウントを保護しています。

## 1. useDemoGuard — フロントエンドの操作制限

```typescript
// hooks/useDemoGuard.ts
import { useSession } from 'next-auth/react';
import { useToast } from '@/components/ToastProvider';

const DEMO_EMAIL = 'demo@example.com';

export function useDemoGuard() {
  const { data: session } = useSession();
  const { showToast } = useToast();

  const isDemo = session?.user?.email === DEMO_EMAIL;

  const guardAction = (action: () => void) => {
    if (isDemo) {
      showToast('デモアカウントではこの操作はできません');
      return;
    }
    action();
  };

  return { isDemo, guardAction };
}
```

### 使い方

```tsx
function FocusPointsCard() {
  const { isDemo, guardAction } = useDemoGuard();

  const handleAdd = () => {
    guardAction(() => {
      // 実際の追加処理
      addFocusPoint(text);
    });
  };

  return (
    <Button onClick={handleAdd} disabled={isDemo}>
      追加
    </Button>
  );
}
```

**ポイント**: ボタンの `disabled` で視覚的にも制限を示しつつ、`guardAction` で二重に防御。ユーザーが DevTools でボタンを有効化しても、トースト通知で制限を伝えます。

## 2. APIレベルの制限

フロントエンドの制限は突破可能なので、API 側でも制限します。

```typescript
// lib/api-middleware.ts
export function withAuth(
  handler: (req: NextRequest, context: AuthContext) => Promise<NextResponse>
) {
  return async (req: NextRequest) => {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // デモユーザーの書き込み制限
    if (
      session.user.email === DEMO_EMAIL &&
      ['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)
    ) {
      return NextResponse.json(
        { error: 'デモアカウントでは変更できません' },
        { status: 403 }
      );
    }

    return handler(req, { userId: session.user.id, role: session.user.role });
  };
}
```

## 3. JWTカスタムクレームの活用

NextAuth のセッションにデモフラグを含めることで、サーバーサイドでの判定を効率化:

```typescript
// auth設定
callbacks: {
  async jwt({ token, user }) {
    if (user) {
      token.role = user.role;
      token.isDemo = user.email === DEMO_EMAIL;
    }
    return token;
  },
  async session({ session, token }) {
    session.user.role = token.role;
    session.user.isDemo = token.isDemo;
    return session;
  },
},
```

## 4. 日次データリセット — Cron ジョブ

デモアカウントのデータは使っているうちに汚れていきます。毎日 Cron ジョブでリセット:

```typescript
// app/api/cron/reset-demo/route.ts
export const GET = withCronAuth(async () => {
  const demoUserId = await getDemoUserId();

  // 1. ユーザーが作成したデータを削除
  await deleteSubcollection(`users/${demoUserId}/goals`);
  await deleteSubcollection(`users/${demoUserId}/focusPoints`);

  // 2. デモ用の初期データを再投入
  await seedDemoData(demoUserId);

  // 3. プロフィールをリセット
  await adminDb.doc(`users/${demoUserId}`).update({
    displayName: 'デモユーザー',
    onboardingCompleted: false,
  });

  return NextResponse.json({ status: 'ok' });
});
```

### Vercel Cron 設定

```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/reset-demo",
      "schedule": "0 1 * * *"
    }
  ]
}
```

毎日 UTC 01:00（JST 10:00）にリセットが実行されます。

## 5. デモアカウントの UX 工夫

### 制限表示バナー

```tsx
{isDemo && (
  <Alert severity="info" sx={{ mb: 2 }}>
    デモアカウントで閲覧中です。データの変更はできません。
  </Alert>
)}
```

### 操作不可時のフィードバック

単にエラーを出すのではなく、「デモアカウントでは〜」と具体的に制限理由を伝えます。これにより、バグではなく意図的な制限だとユーザーに理解してもらえます。

## まとめ

| 層 | 手法 | 防御対象 |
|----|------|---------|
| フロントエンド | `useDemoGuard` | 通常ユーザーの誤操作 |
| API | `withAuth` ミドルウェア | 直接 API 呼び出し |
| データ | Cron リセット | データの劣化・破損 |

デモアカウントは3層防御で設計すると、安全かつメンテナンスしやすくなります。ポートフォリオアプリにデモアカウントを実装する際の参考になれば幸いです。

---
title: "Playwright E2Eテスト導入 — Next.js App Router + Firebase Auth環境での実践"
emoji: "🎭"
type: "tech"
topics: ["nextjs", "typescript", "個人開発"]
published: true
---

## はじめに

個人開発のWebアプリにE2Eテストを導入するのは「やるべきだけど後回しにしがち」な作業の代表格です。

この記事では、ダーツプレイヤー向けWebアプリ **darts Lab**（Next.js 16 + Firebase Auth + MUI 7）にPlaywrightを導入した実践を共有します。

## 技術スタック

- **Next.js 16** (App Router)
- **Firebase Auth** + **NextAuth** (認証)
- **Playwright** (E2Eテスト)
- **axe-core** (アクセシビリティテスト)
- **GitHub Actions** (CI)

## テスト戦略

### テストピラミッド

```
        ┌──────┐
        │ E2E  │  ← Playwright（主要フロー）
       ┌┴──────┴┐
       │ UI Test │  ← Storybook（コンポーネント）
      ┌┴────────┴┐
      │ Unit Test │  ← Vitest（ロジック）
      └──────────┘
```

E2Eテストは **主要ユーザーフロー** に絞り、網羅的なテストは Unit / Storybook に任せます。

## セットアップ

### Playwright 設定

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Firebase Auth の壁

最大の課題は **Firebase Auth を使った認証済み画面のテスト** です。

#### 解決策: 公開ページのスモークテスト + 認証バイパス

```typescript
// e2e/smoke.spec.ts — 認証不要のテスト
test('ホームページが表示される', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/darts Lab/i);
});

test('ログインページが表示される', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: /ログイン/i }))
    .toBeVisible();
});
```

認証済み画面のテストは、テスト用の環境変数でセッションをモックするか、デモアカウントを使います。

## テストパターン

### 1. ナビゲーションテスト

```typescript
// e2e/navigation.spec.ts
test('主要ページへのナビゲーション', async ({ page }) => {
  await page.goto('/');

  // バレル検索への遷移
  await page.getByRole('link', { name: 'バレル検索' }).click();
  await expect(page).toHaveURL('/barrels');

  // 料金プランへの遷移
  await page.goto('/pricing');
  await expect(
    page.getByRole('heading', { name: /料金/i })
  ).toBeVisible();
});
```

### 2. アクセシビリティテスト

```typescript
// e2e/accessibility.spec.ts
import AxeBuilder from '@axe-core/playwright';

test('ホームページにa11y違反がないこと', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();

  const critical = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious'
  );
  expect(critical).toEqual([]);
});
```

### 3. レスポンシブテスト

Playwright の `projects` 設定でモバイル端末をシミュレート:

```typescript
projects: [
  { name: 'Desktop', use: { ...devices['Desktop Chrome'] } },
  { name: 'Mobile', use: { ...devices['iPhone 13'] } },
],
```

## CI統合

### GitHub Actions

```yaml
# .github/workflows/ci.yml（抜粋）
- name: Playwright をインストール
  run: npx playwright install --with-deps chromium

- name: E2E テスト
  run: npx playwright test
```

### ポイント
- **Chromium のみインストール** — 全ブラウザをインストールすると CI 時間が倍増
- **リトライ 2 回** — CI 環境でのフレーキーテスト対策
- **ワーカー 1** — CI では並列実行を避けて安定性を優先

## テスト実行

```bash
# 全テスト実行
npx playwright test

# 特定のテストファイル
npx playwright test e2e/smoke.spec.ts

# UIモードで実行（デバッグ時に便利）
npx playwright test --ui

# HTMLレポート表示
npx playwright show-report
```

## よくあるハマりポイント

### 1. `waitForLoadState` の使い分け

```typescript
// ❌ ページ遷移後にすぐアサート → 失敗しがち
await page.goto('/barrels');
await expect(page.getByText('バレル')).toBeVisible();

// ✅ ネットワークが落ち着くまで待つ
await page.goto('/barrels');
await page.waitForLoadState('networkidle');
await expect(page.getByText('バレル')).toBeVisible();
```

### 2. MUI コンポーネントのセレクター

MUI は内部で複数の DOM 要素を生成するため、`getByRole` が最も安定:

```typescript
// ❌ クラス名やデータ属性は MUI のバージョンで変わる
page.locator('.MuiButton-root');

// ✅ ロールベースのセレクター
page.getByRole('button', { name: 'ログイン' });
page.getByRole('heading', { name: /料金/i });
```

### 3. CSR コンポーネントの待機

`'use client'` コンポーネントはハイドレーション後に描画されるため、適切な待機が必要:

```typescript
// Skeleton → 実コンテンツの遷移を待つ
await page.waitForSelector('[data-testid="content-loaded"]');
```

## まとめ

| 項目 | 方針 |
|------|------|
| テスト対象 | 主要ユーザーフロー + 公開ページ |
| 認証済み画面 | デモアカウント or セッションモック |
| CI | Chromium のみ、リトライ 2 回 |
| a11y | axe-core で WCAG 2.1 AA 準拠チェック |
| セレクター | `getByRole` 優先 |

E2Eテストは「全画面を網羅する」のではなく、「壊れると困る主要フロー」に絞るのがコツです。個人開発でも CI に組み込むことで、安心してリファクタリングできる環境が手に入ります。

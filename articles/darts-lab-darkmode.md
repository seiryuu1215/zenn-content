---
title: "MUI v7 ダークモード完全対応 — 167箇所のハードコード色をテーマトークンに移行した実践"
emoji: "🌙"
type: "tech"
topics: ["react", "typescript", "個人開発"]
published: true
---

## はじめに

MUI (Material UI) でダークモード対応をする際、最大の敵は**ハードコードされたカラー値**です。

`color: '#333'` や `bgcolor: 'rgba(0,0,0,0.1)'` のような値は、ライトモードでは問題なく見えますが、ダークモードに切り替えた瞬間に読めなくなります。

この記事では、ダーツプレイヤー向けWebアプリ **darts Lab** で実施した、167箇所のハードコード色をテーマトークンに移行した実践を共有します。

## Before / After

### Before（ハードコード）

```tsx
// ❌ ダークモードで見えなくなる
<Typography sx={{ color: '#333' }}>テキスト</Typography>
<Box sx={{ bgcolor: 'rgba(0,0,0,0.05)' }}>背景</Box>
<Divider sx={{ borderColor: '#e0e0e0' }} />
```

### After（テーマトークン）

```tsx
// ✅ テーマに応じて自動切替
<Typography sx={{ color: 'text.primary' }}>テキスト</Typography>
<Box sx={{ bgcolor: alpha(theme.palette.text.primary, 0.05) }}>背景</Box>
<Divider sx={{ borderColor: 'divider' }} />
```

## 移行パターン集

### パターン1: テキスト色

```tsx
// ❌ Bad
color: '#1a1a1a'
color: '#333'
color: '#666'
color: '#999'

// ✅ Good
color: 'text.primary'    // 主要テキスト
color: 'text.secondary'  // 補助テキスト
color: 'text.disabled'   // 無効テキスト
```

### パターン2: 背景色

```tsx
// ❌ Bad
bgcolor: '#f5f5f5'
bgcolor: 'white'
bgcolor: 'rgba(0,0,0,0.04)'

// ✅ Good
bgcolor: 'background.paper'   // カード・パネル背景
bgcolor: 'background.default' // ページ背景
bgcolor: alpha(theme.palette.text.primary, 0.04) // 微妙な背景
```

### パターン3: ボーダー

```tsx
// ❌ Bad
border: '1px solid #e0e0e0'
borderColor: 'rgba(0,0,0,0.12)'

// ✅ Good
borderColor: 'divider'
border: (theme) => `1px solid ${theme.palette.divider}`
```

### パターン4: 透明度付きカラー

`alpha()` ユーティリティが非常に便利です。

```tsx
import { alpha } from '@mui/material/styles';

// ❌ Bad
bgcolor: 'rgba(25, 118, 210, 0.1)' // primary の rgba 直書き

// ✅ Good
bgcolor: alpha(theme.palette.primary.main, 0.1)
```

### パターン5: 条件分岐が必要なケース

```tsx
// ❌ Bad
bgcolor: theme.palette.mode === 'dark' ? '#333' : '#f5f5f5'

// ✅ Good（多くの場合、分岐不要にできる）
bgcolor: 'action.hover'        // MUI が自動で切替
bgcolor: 'background.paper'    // テーマで定義済み
```

## FOUC（Flash of Unstyled Content）防止

ダークモード対応で最も厄介な問題が **FOUC** — ページ読み込み時に一瞬ライトモードが表示されてしまう現象です。

### 解決策: インラインスクリプトでの事前判定

```tsx
// app/layout.tsx
const themeInitScript = `(function(){
  try {
    var s = localStorage.getItem('colorMode');
    var d = s || (matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light');
    if (d === 'dark')
      document.documentElement.setAttribute('data-theme', 'dark');
  } catch(e) {}
})()`;

// CSS で即座にダーク背景を適用
// globals.css
// html[data-theme='dark'] body { background-color: #121212; }
```

React のハイドレーション前にダーク背景を適用するため、ちらつきが発生しません。

## テーマの設計

```tsx
// components/Providers.tsx
const getDesignTokens = (mode: 'light' | 'dark') => ({
  palette: {
    mode,
    ...(mode === 'dark'
      ? {
          background: {
            default: '#121212',
            paper: '#1e1e1e',
          },
        }
      : {
          background: {
            default: '#fafafa',
            paper: '#ffffff',
          },
        }),
  },
});
```

## 移行の進め方

167箇所を一気に変更するのではなく、段階的に進めました:

1. **Phase 1**: レイアウト系（Header, Footer） — 影響範囲が全ページ
2. **Phase 2**: ホーム画面 — 最も見られる画面
3. **Phase 3**: スタッツ・カレンダー — データ表示系
4. **Phase 4**: 機能ページ — バレル検索、セッティング等

### grep で残存ハードコードを検出

```bash
# ハードコード色の検出
grep -rn "color: '#" components/ app/ --include="*.tsx" | grep -v node_modules
grep -rn "bgcolor: '#" components/ app/ --include="*.tsx"
grep -rn "rgba(" components/ app/ --include="*.tsx" | grep -v alpha
```

## まとめ

| 変更パターン | Before | After |
|------------|--------|-------|
| テキスト色 | `'#333'` | `'text.primary'` |
| 背景色 | `'#f5f5f5'` | `'background.paper'` |
| ボーダー | `'#e0e0e0'` | `'divider'` |
| 透明度 | `'rgba(...)'` | `alpha(theme.palette.xxx, 0.1)` |
| 条件分岐 | `mode === 'dark' ? ... : ...` | `'action.hover'` |

ダークモード対応は地道な作業ですが、テーマトークンに統一することで保守性が大幅に向上します。新しいコンポーネントを追加する際も、テーマトークンを使えば自動的にダークモード対応になります。

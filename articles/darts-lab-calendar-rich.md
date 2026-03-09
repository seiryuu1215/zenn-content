---
title: "カレンダーUIのリッチ化 — GitHub Contributions風から詳細パネル付きへの進化"
emoji: "📅"
type: "tech"
topics: ["react", "typescript", "個人開発"]
published: true
---

## はじめに

ダーツプレイヤー向けWebアプリ **darts Lab** には、練習記録をカレンダー形式で表示する機能があります。

当初は GitHub の Contributions グラフ風のシンプルな表示でしたが、ユーザーからのフィードバックを受けて、詳細スタッツ表示やアワードバッジなどを追加したリッチなUIに進化させました。

この記事では、カレンダーUIのリッチ化で得た知見を共有します。

## Before / After

### Before
- 日付セルの濃淡でゲーム数を可視化（GitHub風）
- ポップオーバーは Rating / ゲーム数 / コンディション のみ
- 詳細パネルは Rating / PPD / MPR の 3 指標のみ

### After
- 全 20+ フィールドをAPI から取得
- ポップオーバーに PPD / MPR のサマリーを追加
- 詳細パネルをセクション分け（01, Cricket, ブル, アワード）
- アワードはチップ風バッジで表示、高難度アワードをハイライト

## 1. API 拡張 — フィールドの追加

元々 10 フィールドのみ返していた API を、Firestore に存在する全フィールドを取得するように拡張:

```typescript
// app/api/stats-calendar/route.ts
records.push({
  id: doc.id,
  date: dateVal ? dateVal.toISOString() : '',
  // 既存
  rating: rawRating != null ? parseFloat(String(rawRating)) : null,
  ppd: d.zeroOneStats?.ppd ?? null,
  mpr: d.cricketStats?.mpr ?? null,
  gamesPlayed: d.gamesPlayed ?? 0,
  condition: d.condition ?? null,
  // 新規追加
  bullRate: d.bullRate ?? null,
  avg01: d.zeroOneStats?.avg ?? null,
  highOff: d.zeroOneStats?.highOff ?? null,
  cricketHighScore: d.cricketStats?.highScore ?? null,
  ton80: d.ton80 ?? 0,
  lowTon: d.lowTon ?? 0,
  highTon: d.highTon ?? 0,
  hatTrick: d.hatTricks ?? 0,
  threeInABed: d.threeInABed ?? 0,
  threeInABlack: d.threeInABlack ?? 0,
  whiteHorse: d.whiteHorse ?? 0,
});
```

### Rating 小数点修正

Firestore では Rating が文字列として保存されているケースがあり、`Number()` 変換で小数が欠落していました。`parseFloat(String(rawRating))` で修正:

```typescript
// ❌ Before: Number() だと "5.67" → 5 になるケースがあった
rating: d.rating ?? null,

// ✅ After: parseFloat で確実に小数を保持
rating: rawRating != null ? parseFloat(String(rawRating)) : null,
```

## 2. 同日マージロジック

1 日に複数セッションをプレイすると、複数のレコードが存在します。表示時にマージが必要:

```typescript
// マージルール
// - condition: 最大値（最も良い方を採用）
// - rating: 後勝ち（最新の値）
// - gamesPlayed: 合計
// - dBull, sBull: 合計
// - highOff, cricketHighScore: 最大値
// - ton80, lowTon, etc.: 合計（アワード系）
// - ppd, mpr, bullRate: 後勝ち（平均系）
```

ヘルパー関数で null 安全に集計:

```typescript
function sumNullable(a: number | null, b: number | null): number | null {
  if (a == null && b == null) return null;
  return (a ?? 0) + (b ?? 0);
}

function maxNullable(a: number | null, b: number | null): number | null {
  if (a == null) return b;
  if (b == null) return a;
  return Math.max(a, b);
}
```

## 3. 詳細パネルのセクション設計

DayDetailPanel をセクション分けしてリッチ化:

```
┌────────────────────────────┐
│ Rating 5.67    ★★★★☆ いい感じ │  ← ヘッダー
├────────────────────────────┤
│      総ゲーム数: 15         │  ← ゲーム概要
├────────────────────────────┤
│ 01 スタッツ                 │
│ PPD: 21.50 | 平均: 450 | HO: 120 │
├────────────────────────────┤
│ Cricket スタッツ             │
│ MPR: 2.10 | HS: 3.50        │
├────────────────────────────┤
│ ブルスタッツ                 │
│ D: 12 | S: 8 | 合計: 20     │
│ ブル率: 35.2%               │
├────────────────────────────┤
│ アワード                    │
│ [ロートン ×3] [ハイトン ×1]   │
│ [TON80 ×0] [HT ×0]          │  ← 0回はグレーアウト
│ [3itB ×1]                   │  ← 高難度はゴールド
├────────────────────────────┤
│ メモ: 今日は調子良かった      │
│ 課題: ブル率向上             │
└────────────────────────────┘
```

### アワードのスタイリング

MUI の `Chip` コンポーネントを活用し、達成状況に応じたスタイルを適用:

```tsx
const RARE_AWARDS = new Set(['TON80', '3 in the Black', 'ホワイトホース']);

<Chip
  label={`${award.label} ×${award.count}`}
  size="small"
  variant={hasCount ? 'filled' : 'outlined'}
  sx={{
    // 高難度アワード（達成時）→ ゴールドハイライト
    ...(hasCount && isRare ? {
      bgcolor: alpha(theme.palette.warning.main, 0.15),
      color: theme.palette.warning.main,
      fontWeight: 700,
    }
    // 通常アワード（達成時）→ グリーン
    : hasCount ? {
      bgcolor: alpha(theme.palette.success.main, 0.1),
      color: theme.palette.success.main,
    }
    // 未達成 → グレーアウト
    : { opacity: 0.4 }),
  }}
/>
```

## 4. ポップオーバーの強化

カレンダーのセルをクリックしたときのポップオーバーにも主要スタッツを追加:

```tsx
<Popover>
  <Box sx={{ p: 1.5, minWidth: 160 }}>
    <Typography variant="subtitle2" fontWeight="bold">
      {date}
    </Typography>
    {rating && <Typography>Rating: {rating.toFixed(2)}</Typography>}
    <Typography>ゲーム数: {gamesPlayed}</Typography>
    {ppd && <Typography>PPD: {ppd.toFixed(2)}</Typography>}
    {mpr && <Typography>MPR: {mpr.toFixed(2)}</Typography>}
    <Typography>コンディション: {conditionLabel}</Typography>
    <Typography variant="caption" color="primary">
      クリックで詳細を表示
    </Typography>
  </Box>
</Popover>
```

## 5. PDF エクスポート

カレンダーページに月次レポートの PDF ダウンロードボタンも追加しました。Puppeteer でサーバーサイド PDF 生成を行い、月間サマリー・スタッツ・アワード集計を A4 レポートとして出力します。

## まとめ

| 改善ポイント | Before | After |
|------------|--------|-------|
| API フィールド数 | 10 | 22 |
| 詳細パネル | Rating/PPD/MPR のみ | 6セクション構成 |
| アワード表示 | なし | チップバッジ（グレーアウト + ハイライト） |
| ポップオーバー | 3項目 | 6項目 + 詳細リンク |
| PDF出力 | なし | 月次レポート対応 |

カレンダーUIは「データがある日をハイライトする」だけでも十分機能しますが、詳細データの深掘りができるとユーザーの練習振り返りに大きく貢献します。段階的にリッチ化していく進め方がおすすめです。

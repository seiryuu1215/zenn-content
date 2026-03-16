---
title: "Test Agent: 2,100+テストの品質保証"
---

## Test Agentの役割

Test Agentは「コードを編集できないQAエンジニア」だ。

Implement Agentが実装したコードに対して、テストファイルを新規作成し、全テストがパスすることを確認する。それがTest Agentの全仕事だ。実装コードには一切手を加えない。テストが失敗したら、Implement Agentに差し戻す。

この「実装コードに触れない」制約こそが、Test Agentの品質を担保する。実装者がテストを書くと、無意識に「自分のコードが正しい前提」でテストを組み立ててしまう。Test Agentは実装の内部構造を知らない外部の視点でテストを書くため、エッジケースや境界値の見落としが少ない。

DevDexの開発では、Test Agentが150ファイル・2,100+件のユニットテストを出力した。v0のMVP段階で403件、v1完了時に496件、v3完了時に1,316件、公開準備完了時には1,407件、機能追加で1,813件、そして品質強化を経て2,100+件に達した。

## エージェント定義

```markdown
---
name: test-agent
description: 実装に対してTDDでテストを書き全件通ることを確認する。
tools: Read, Bash, Glob
skills:
  - test-patterns
---

あなたはこのプロジェクトのQAエンジニアです。

役割：
- 可能な限り実装前にテストを先に書く（TDD）
- 全テストが通ることを確認してから review-agent に引き渡す
- テスト結果（件数・Pass/Fail・気づき）を docs/diary/YYYY-MM-DD.md に追記する
```

注目すべきは `tools: Read, Bash, Glob` の行だ。Test Agentが使えるツールは3つだけ。

| ツール | 用途 |
|---|---|
| `Read` | 実装コードを読んで仕様を理解する |
| `Bash` | テストファイルの作成と `npm run test:unit` の実行 |
| `Glob` | テスト対象のファイルを検索する |

`Edit` と `Write` が含まれていないことに気づくかもしれないが、`Bash` でファイル作成が可能なため、テストファイルの新規作成はできる。一方で、既存の実装コードを `Edit` で修正することはできない。この非対称な制限が「テストだけに集中する」環境を作り出す。

`skills: test-patterns` により、Vitest 4 + Testing Libraryの書き方ルールが自動的に適用される。

```markdown
## 書き方ルール
- describe/itブロックを使う（testではなくit）
- テスト名は日本語「〜すること」形式
- モック: vi.mock()を使う。any禁止
- 非同期: async/await形式
```

テスト名を日本語にしたのは意図的な判断だ。「it('should return 401 when not authenticated')」よりも「it('認証なしで401を返すこと')」のほうが、テスト失敗時のログが読みやすい。日本語UIの日本語テスト名は、仕様書としても機能する。

## テストパターン: APIルート

DevDexの63本のAPIエンドポイントには、すべてテストが書かれている。APIルートのテストは最も量が多く、全体の約半数を占める。

### モック設定のパターン

APIルートのテストでは、Supabaseクライアントと認証関数をモックする。DevDex全体で統一されたモックパターンを示す。

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

// 認証モック
const mockCheckAuth = vi.fn();
vi.mock('@/lib/auth', () => ({
  checkAuth: (...args: unknown[]) => mockCheckAuth(...args),
}));

// Supabaseモック
const mockFrom = vi.fn();
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn().mockResolvedValue({
    from: (...args: unknown[]) => mockFrom(...args),
  }),
}));
```

2つのポイントがある。

**1. `vi.fn()` をモジュールスコープで定義する。** `vi.mock()` はモジュール単位で巻き上げられる（hoisted）ため、コールバック内で外部変数を参照するには、`vi.fn()` で宣言した変数を使う必要がある。

**2. `any` を使わない。** `(...args: unknown[])` という型注釈で、`test-patterns` スキルの「any禁止」ルールを遵守している。Implement Agentにもこのスキルが共有されているため、テスト対象のコードも `unknown` + 型ガードで書かれており、テスト側で型の不整合が起きにくい。

### 認証テスト

すべてのAPIテストに含まれる共通パターンが「認証なしで401を返すこと」のテストだ。

```typescript
it('認証なしで401を返すこと', async () => {
  const { NextResponse } = await import('next/server');
  mockCheckAuth.mockResolvedValue({
    authenticated: false,
    response: NextResponse.json(
      { data: null, error: '認証が必要です' },
      { status: 401 }
    ),
  });

  const { POST } = await import('./route');
  const res = await POST(createRequest({ name: 'React' }));
  expect(res.status).toBe(401);
});
```

63本のAPIすべてにこのテストが存在する。冗長に見えるかもしれないが、このテストが実際にバグを防いだ。v1のレビューで「POST /api/terms で user_id を設定していない」というCritical指摘があったとき、テスト側で `checkAuth()` の戻り値に `userId` が含まれることを前提としたテストが既にあったため、修正後の回帰テストが不要だった。

### バリデーションテスト

APIへの不正な入力に対するテストも網羅的に書く。

```typescript
it('name未指定で400を返すこと', async () => {
  const { POST } = await import('./route');
  const res = await POST(createRequest({ category: 'frontend' }));
  const json = await res.json();

  expect(res.status).toBe(400);
  expect(json.data).toBeNull();
  expect(json.error).toBe('用語名は必須です');
});

it('nameが空文字で400を返すこと', async () => {
  const { POST } = await import('./route');
  const res = await POST(
    createRequest({ name: '  ', category: 'frontend' })
  );
  const json = await res.json();

  expect(res.status).toBe(400);
  expect(json.error).toBe('用語名は必須です');
});

it('category未指定で400を返すこと', async () => {
  const { POST } = await import('./route');
  const res = await POST(createRequest({ name: 'SomeLib' }));
  expect(res.status).toBe(400);
});
```

空文字、空白のみ、未指定、無効な値。これらのバリデーションテストは「正常系が動く」ことだけでなく「異常系で適切に拒否する」ことを保証する。

### ヘルパー関数

テストファイル内に頻出するヘルパー関数がある。テスト用のRequest生成と、モックデータ生成だ。

```typescript
/** テスト用Requestを生成 */
function createRequest(body: unknown): Request {
  return new Request('http://localhost:3000/api/terms/ai-overview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
```

診断機能のテストでは、さらに複雑なヘルパーを用意した。

```typescript
/** 全問同じ値で回答を生成する */
function createUniformAnswers(value: number): number[] {
  return Array.from({ length: 20 }, () => value);
}

/** 特定の軸だけ異なる値を持つ回答を生成する */
function createAnswersWithAxisValue(
  defaultValue: number,
  axisOverrides: Partial<Record<string, number>>,
): number[] {
  const answers = createUniformAnswers(defaultValue);
  const axisRanges: Record<string, number[]> = {
    design_vs_impl: [0, 1, 2, 3, 4],
    front_vs_back: [5, 6, 7, 8, 9],
    breadth_vs_depth: [10, 11, 12, 13, 14],
    creative_vs_reproduce: [15, 16, 17, 18, 19],
  };

  for (const [axis, value] of Object.entries(axisOverrides)) {
    const indices = axisRanges[axis];
    if (indices) {
      for (const idx of indices) {
        answers[idx] = value;
      }
    }
  }
  return answers;
}
```

このヘルパーにより、「全問3で回答した場合」「設計軸だけ5にした場合」など、多様な診断パターンを簡潔にテストできる。16タイプ x 各軸のエッジケースを手動で書いていたら膨大な量になるが、ヘルパーがテストの可読性と保守性を支えた。

## テストパターン: コンポーネント

コンポーネントテストは37ファイル。Testing Libraryの `render`, `screen`, `fireEvent`, `waitFor` を中心に構成される。

### レンダリングとユーザー操作

```typescript
import { render, screen, fireEvent, waitFor }
  from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

describe('TermForm', () => {
  it('カテゴリを選択できること', async () => {
    render(<TermForm onSubmit={mockOnSubmit} />);

    const select = screen.getByRole('combobox');
    fireEvent.click(select);

    const option = screen.getByText('フロントエンド');
    fireEvent.click(option);

    expect(select).toHaveTextContent('フロントエンド');
  });
});
```

ポイントは `@testing-library/jest-dom/vitest` のインポートだ。これにより `toHaveTextContent`, `toBeInTheDocument`, `toBeDisabled` などのカスタムマッチャーが使える。Vitestの設定ファイルではなく、各テストファイルの先頭でインポートする方式を採用した。

### 非同期処理のテスト

fetch APIを使うコンポーネントのテストでは、`waitFor` が多用される。

```typescript
it('検索結果を表示すること', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      data: [{ id: '1', name: 'React', category: 'frontend' }],
      error: null,
    }),
  });

  render(<Header />);

  const input = screen.getByPlaceholderText('用語を検索');
  fireEvent.change(input, { target: { value: 'React' } });

  await waitFor(() => {
    expect(screen.getByText('React')).toBeInTheDocument();
  });
});
```

`mockFetch.mockResolvedValueOnce()` で1回だけのモック応答を設定し、`waitFor` で非同期更新後のDOMを検証する。DevDexではdebounce付きの検索コンポーネントが複数あるため、debounceフック自体をモックして即座に値を返すようにしている。

```typescript
vi.mock('@/lib/hooks/use-debounce', () => ({
  useDebounce: (value: string) => value,
}));
```

このモックがないと、テスト内でタイマーの制御が必要になり、flaky testの温床になる。

## テストパターン: ユーティリティ関数

ライブラリ層（`src/lib/`）のテストは最も書きやすく、最も信頼性が高い。外部依存がないか少ないため、モックなしで純粋なロジックテストが書ける。

```typescript
describe('ENGINEER_TYPES', () => {
  it('16タイプが定義されていること', () => {
    expect(Object.keys(ENGINEER_TYPES)).toHaveLength(16);
  });

  it('各タイプにcode, name, description, strengths(3つ), catchupが設定されていること', () => {
    for (const type of Object.values(ENGINEER_TYPES)) {
      expect(type.code).toBeTruthy();
      expect(type.name).toBeTruthy();
      expect(type.description).toBeTruthy();
      expect(type.strengths).toHaveLength(3);
      expect(type.catchup).toBeTruthy();
    }
  });
});
```

Feature Gateのテストは、全ロール x 全機能の組み合わせを網羅的にテストしている。

```typescript
describe('canAccessFeature', () => {
  describe('free ユーザー（user ロール）', () => {
    const role: UserRole = 'user';

    it('Pro機能にアクセスできないこと', () => {
      expect(canAccessFeature(role, 'public-profile')).toBe(false);
      expect(canAccessFeature(role, 'pdf-export')).toBe(false);
      expect(canAccessFeature(role, 'excel-export')).toBe(false);
    });

    it('Enterprise機能にアクセスできないこと', () => {
      expect(canAccessFeature(role, 'candidate-search')).toBe(false);
      expect(canAccessFeature(role, 'candidate-compare')).toBe(false);
    });
  });

  describe('admin ユーザー', () => {
    const role: UserRole = 'admin';

    it('Pro機能にアクセスできること', () => {
      expect(canAccessFeature(role, 'public-profile')).toBe(true);
      expect(canAccessFeature(role, 'pdf-export')).toBe(true);
    });

    it('Enterprise機能にアクセスできること', () => {
      expect(canAccessFeature(role, 'candidate-search')).toBe(true);
    });
  });
});
```

このテストがあることで、権限マトリクスの変更時に「Free ユーザーにPro機能が開放されてしまう」リグレッションを即座に検出できる。PM Agentが `docs/decisions/2026-03-12-role-permissions.md` で定義した権限マトリクスが、テストコードとして実装されている形だ。

## 2,100+テストの内訳

150のテストファイルを分類すると、以下の構成になる。

| カテゴリ | ファイル数 | 主なテスト内容 |
|---|---|---|
| APIルート | 30 | 認証、バリデーション、CRUD、権限チェック |
| コンポーネント | 42 | レンダリング、ユーザー操作、非同期更新 |
| ユーティリティ | 28 | バリデーション、計算ロジック、型変換 |
| 型定義 | 1 | 型定義の整合性 |
| その他（RLS等） | 17 | ミドルウェア、RLSポリシー、認証ヘルパー |

テスト数の推移は開発フェーズと一致する。

```
v0 MVP:    403件（CRUD API + コアUI）
v1:        496件（マスターデータ + 関連用語）
v2:       1,025件（診断 + スキルシート + 公開プロフィール）
v3:       1,316件（組織機能 + Feature Gate + Admin）
公開準備: 1,407件（LP + オンボーディング + 診断デモグラフィック）
機能追加: 1,813件（ダッシュボード改善 + バグ修正 + UI改善）
品質強化: 2,100+件（Pro限定機能 + AI機能拡充 + テスト網羅性向上）
```

v2からv3にかけてテスト数が急増しているのは、権限・ロールの組み合わせテストが爆発的に増えたためだ。3つの個人ロール x 4つの組織ロール x 11の機能ゲート。これらの組み合わせを網羅するテストは、手動では到底書ききれない量だが、Test Agentはパターンを認識して体系的に生成した。

## テストが実装を守った実例

Test Agentが書いたテストが、実際にバグを防いだ事例を2つ紹介する。

### 事例1: Feature Gate変更時のリグレッション検出

v3のPhase 2で `feature-gate.ts` にExcelエクスポートと診断詳細を追加したとき、既存のFeature Gateテストが即座にリグレッションを検出した。新しい機能名を `FEATURE_PLAN_MAP` に追加した際、Pro以上のプランでのみアクセス可能にするつもりが、初期実装でEnterprise限定になっていた。テストの `expect(canAccessFeature('pro', 'excel-export')).toBe(true)` が失敗して問題が発覚した。

### 事例2: Supabaseチェインモックの不整合

APIルートのリファクタリングで、Supabaseのクエリチェーンの順序を変更したとき（`.select().eq().order()` を `.select().order().eq()` に変更）、テスト側のモックチェーンが不整合になりテストが失敗した。これ自体はテストの修正が必要な「偽陽性」だが、実装の変更が意図的なものかどうかを確認するきっかけになった。

## テスト実行とカバレッジ方針

DevDexではカバレッジの数値目標を設けていない。代わりに「全APIの正常系・異常系・認証テスト」「全コンポーネントのレンダリングテスト」「全バリデーション関数のテスト」という観点ベースのカバレッジを追求した。

この判断にはTest Agentの特性が影響している。Test Agentはカバレッジレポートを解析するよりも、実装コードを読んで「この関数にはどんなテストが必要か」を判断するほうが得意だ。カバレッジの数値を追うと、テストの質より量に偏りがちになる。

テストの実行は Vitest 4 の並列実行で高速に処理される。150ファイル・2,100+件のテストが、ローカル環境で約15秒以内に完了する。この速度があるからこそ、Implement Agentのフック設定（テストファイル書き込み時に自動実行）が実用的に機能する。

## Tips

### テストファイルの配置規約

DevDexではテストファイルを実装ファイルと同じディレクトリに配置する。

```
src/app/api/terms/
  ├── route.ts           # 実装
  └── route.test.ts      # テスト（同じディレクトリ）

src/components/
  ├── term-form.tsx       # 実装
  └── term-form.test.tsx  # テスト（同じディレクトリ）

src/lib/
  ├── feature-gate.ts     # 実装
  └── feature-gate.test.ts # テスト（同じディレクトリ）
```

`__tests__/` ディレクトリに分離する方式は採用しなかった。テストと実装が同じディレクトリにあると、Test AgentがGlobで対象ファイルを見つけやすく、「このファイルにはテストがまだない」という状態を検出しやすい。

### flaky test対策

Test Agentの最大の敵はflaky test（不安定なテスト）だ。DevDexで発生したflaky testと対策を示す。

**1. debounceによるタイミング依存**

対策: debounceフックをモックして即座に値を返す。

```typescript
vi.mock('@/lib/hooks/use-debounce', () => ({
  useDebounce: (value: string) => value,
}));
```

**2. `import()` の動的インポート順序**

Next.jsのRoute Handlersをテストする際、`vi.mock()` のhoisting順序と動的 `import()` の相互作用でテストが不安定になることがある。対策として、各 `it` ブロック内で `await import('./route')` を呼び出し、テストごとにモジュールを再読み込みする。

```typescript
it('認証なしで401を返すこと', async () => {
  mockCheckAuth.mockResolvedValue({ authenticated: false });

  const { POST } = await import('./route');
  const res = await POST(createRequest({}));
  expect(res.status).toBe(401);
});
```

**3. `beforeEach` での確実なクリア**

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  mockCheckAuth.mockResolvedValue({
    authenticated: true,
    userId: 'test-user-id',
    role: 'user',
  });
});
```

`vi.clearAllMocks()` で前のテストのモック状態をリセットし、デフォルトの認証状態を再設定する。この2行がないと、テストの実行順序に依存する不安定なテストが生まれる。

### Test AgentとImplement Agentの分離がもたらす効果

Test Agentを独立させた最大の効果は「テストの視点の独立性」だ。

Implement Agentが実装したコードに対して、Test Agentは「仕様を満たしているか」という外部視点でテストを書く。実装の内部構造（private関数の呼び出し順序やローカル変数の状態）には依存しない。

この分離がなければ、「実装に合わせてテストを書く」パターンに陥りやすい。テストが実装の鏡像になってしまい、バグがテストにも複製される。Test Agentは実装コードをReadで読むが、Editで修正することはできない。この制約が「テストを通すために実装を変える」という逆転を防ぐ。

テストが失敗した場合、Test AgentはImplement Agentに差し戻す。差し戻しの判断もTest Agentが行う。「テスト側の問題か、実装側の問題か」を切り分け、実装側の問題であれば具体的な失敗内容とともにImplement Agentに返す。

---

Test Agentが全テストのパスを確認したら、次はReview Agentの出番だ。第6章では「コードを書けないシニアレビュアー」が、どのような観点でコードを審査したかを解説する。

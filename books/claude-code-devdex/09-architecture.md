---
title: "DevDexのアーキテクチャ"
---

## 技術選定の全体像

DevDexの技術スタックは「コスト0で運用でき、将来の拡張に耐える」という制約から選定した。

| レイヤー | 技術 | 選定理由 |
|---|---|---|
| フレームワーク | Next.js 16 (App Router) | Server Components + ファイルシステムルーティング |
| 言語 | TypeScript | 型安全性。エージェントの出力品質にも寄与 |
| DB/Auth | Supabase (PostgreSQL + Auth) | RLS、リレーショナル、無料枠 |
| UI | shadcn/ui + Tailwind CSS v4 | ソースコード手元管理、カスタマイズ自由度 |
| AI | Anthropic API (Claude Haiku) | 構造化出力の安定性、コスト効率 |
| テスト | Vitest 4 + Testing Library | ESModulesネイティブ、高速実行 |
| デプロイ | Vercel | Next.jsとのネイティブ統合、無料枠 |

このスタック全体でランニングコストがゼロに収まる。Supabaseの無料枠（500MB DB、50,000行、50,000月間アクティブユーザー）とVercelの無料枠で、個人開発フェーズではコストが発生しない。唯一のコストはAnthropic APIだが、3段階フォールバック（後述）で呼び出し回数を最小化した。

### なぜNext.js 16か

前作「ダーツラボ」ではPages Routerを使っていたが、DevDexではApp Routerに移行した。最大の理由はServer Components。データの取得と表示だけのコンポーネントをサーバーサイドで完結させ、クライアントに送るJavaScriptを最小限にする。

`'use client'` を付けるのは、フォーム入力、モーダル、タブ切り替えなどインタラクティブなコンポーネントだけ。ページコンポーネント（`page.tsx`）は原則Server Componentで、データフェッチをサーバーサイドで行う。

もう1つの理由がRoute Handlers。`src/app/api/[resource]/route.ts` でREST APIを構築する方式は、将来のExpo（React Native）対応時にそのまま使える。PM Agentが `docs/decisions/2026-03-11-v0-task-breakdown.md` で記録した通り、Server Actionsは「フォームと密結合しすぎる」という理由で却下した。

### なぜSupabaseか

前作のFirebase（Firestore）からの移行理由は明確だ。DevDexのデータモデルは本質的にリレーショナルで、用語（terms）、ユーザー（profiles）、関連用語（term_relations）、組織（organizations）、メンバー（organization_members）の間に複雑な参照関係がある。NoSQLで表現すると非正規化が複雑になりすぎる。

PostgreSQLのRLS（Row Level Security）も決定的だった。RLSにより、データベースレベルでアクセス制御を実現できる。APIのRoute Handlerで認可チェックを忘れても、RLSが最後の防衛線になる。

## DBスキーマ: 22マイグレーションの全体像

22本のマイグレーションで構築されたDevDexのDBは、6つの機能領域に分類できる。

### 領域1: 用語管理（コア）

```sql
-- 用語テーブル
CREATE TABLE terms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  parent_id UUID REFERENCES terms(id) ON DELETE SET NULL,
  category TEXT NOT NULL,
  overview TEXT,
  my_experience TEXT,
  interview_summary TEXT,
  mastery_score SMALLINT CHECK (mastery_score BETWEEN 1 AND 5),
  is_pinned BOOLEAN DEFAULT FALSE,
  ...
);

-- 関連用語（多対多・双方向）
CREATE TABLE term_relations (
  term_id UUID REFERENCES terms(id) ON DELETE CASCADE,
  related_term_id UUID REFERENCES terms(id) ON DELETE CASCADE,
  PRIMARY KEY (term_id, related_term_id)
);
```

`parent_id` と `term_relations` で親子関係（包含）と関連用語（横の繋がり）を明示的に分離した。`term_relations` を配列カラムでなく中間テーブルにした理由は、双方向の関連を扱いやすくするためと、将来 `relation_type`（「含む」「関連する」「前提とする」など）を追加できるようにするためだ。

### 領域2: ユーザー・認証

```sql
CREATE TYPE user_role AS ENUM ('user', 'pro', 'admin');

CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role user_role NOT NULL DEFAULT 'user',
  display_name TEXT,
  username TEXT UNIQUE,
  ...
);
```

`user_role` をENUM型で定義し、`profiles` テーブルで管理する。Supabaseの `raw_user_meta_data` にロールを入れる方法もあるが、DBカラムとして管理することでRLSポリシーから直接参照でき、セキュリティが高い。

profilesテーブルは `auth.users` と1:1で紐づく。ユーザー作成時にトリガーで自動挿入される。これにより、認証後すぐに `profiles.role` で権限チェックができる。

### 領域3: スキルシート

スキルシート機能は5つのテーブルで構成される。

```
skill_sheets         -- 1ユーザー1シート（基本情報、資格、自己PR）
skill_sheet_projects -- 案件経歴（実務/個人開発、期間、担当工程）
project_terms        -- 案件と用語の紐づけ（使用技術）
term_experiences     -- 用語の実務/個人開発分類
```

`skill_sheets` は `user_id` にUNIQUE制約を付け、1ユーザーにつき1シートという設計にした。複数シートを持たせる設計も検討したが、「1人のエンジニアに1つのスキルシート」というドメインの制約に合わせた。

`skill_sheet_projects` の `phases` カラムはJSONB型で、担当工程（要件定義、基本設計、詳細設計、実装、テスト、保守）をチェックリスト形式で保持する。正規化してテーブルを作る方法もあるが、工程の種類が固定的でクエリの必要もないため、JSONBで十分と判断した。

### 領域4: エンジニア診断

```sql
CREATE TABLE engineer_diagnoses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type_code TEXT NOT NULL,
  axis_scores JSONB NOT NULL,
  question_answers JSONB NOT NULL,
  target_type_code TEXT,
  ...
);
```

`axis_scores` と `question_answers` をJSONB型にした理由は、診断ロジックの変更（質問の追加・軸の変更）にスキーマ変更なしで対応するためだ。診断は分析用途がメインで、個別カラムに対するWHERE句は不要。

### 領域5: AI概要補完

```sql
CREATE TABLE ai_overviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  term_name TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,
  overview TEXT NOT NULL,
  ...
);

CREATE TABLE ai_overview_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  used_at TIMESTAMPTZ DEFAULT NOW()
);
```

`ai_overviews` は全ユーザー共有のキャッシュテーブル。`term_name` にUNIQUE制約を付け、同じ用語のAI生成結果を2度呼び出さない。`ai_overview_usage` は1行 = 1回のAPI利用で、サーバーサイドのレート制限管理に使う。

### 領域6: 組織・企業向け

組織機能は4つのテーブルで構成される。

```sql
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  plan TEXT NOT NULL DEFAULT 'free'
    CHECK (plan IN ('free', 'pro', 'enterprise')),
  ...
);

CREATE TABLE organization_members (
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member'
    CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  PRIMARY KEY (organization_id, user_id)
);
```

`organization_members` の複合主キー `(organization_id, user_id)` により、1ユーザーが同じ組織に重複して所属することを防ぐ。ロールはCHECK制約で4種類に限定した。

RLSポリシーは組織単位で設計している。メンバーのみ閲覧可能、admin/ownerのみ追加・削除可能、ownerのみ組織設定変更可能。この階層構造がSQL上で強制される。

## Feature Gate設計

DevDexの収益化設計の核がFeature Gateだ。`src/lib/feature-gate.ts` にすべてのアクセス制御ロジックが集約されている。

```typescript
export type FeatureName =
  | 'public-profile'
  | 'pdf-export'
  | 'excel-export'
  | 'diagnosis-detail'
  | 'candidate-search'
  | 'candidate-compare'
  | 'ats-integration'
  | ...;

export type PlanLevel = 'free' | 'pro' | 'enterprise';

const PLAN_HIERARCHY: Record<PlanLevel, number> = {
  free: 0,
  pro: 1,
  enterprise: 2,
};

export const FEATURE_PLAN_MAP: Record<FeatureName, PlanLevel> = {
  'public-profile': 'pro',
  'pdf-export': 'pro',
  'candidate-search': 'enterprise',
  ...
};

export function canAccessFeature(
  role: UserRole, feature: FeatureName
): boolean {
  const userPlan = getUserPlanLevel(role);
  const requiredPlan = FEATURE_PLAN_MAP[feature];
  return PLAN_HIERARCHY[userPlan] >= PLAN_HIERARCHY[requiredPlan];
}
```

設計のポイントは3つある。

**1. UserRoleからPlanLevelへの変換**。`admin` は `enterprise` 相当として扱う。これによりadminは全機能にアクセスできる。

**2. 階層構造の数値化**。`free: 0, pro: 1, enterprise: 2` の数値比較で「pro以上」「enterprise限定」を判定する。

**3. 個人ロールと組織プランの二軸**。個人の `UserRole`（user/pro/admin）と組織の `plan`（free/pro/enterprise）は独立した軸だ。個人がfreeでも、enterprise組織に所属していれば組織機能は使える。

サーバーサイドでは `checkFeatureAccess()` を使い、403レスポンスを自動生成する。

```typescript
export function checkFeatureAccess(
  role: UserRole, feature: FeatureName
): NextResponse | null {
  if (canAccessFeature(role, feature)) {
    return null;  // アクセス可能
  }
  return NextResponse.json(
    { data: null, error: `「${featureLabel}」機能は${plan}プランで利用できます` },
    { status: 403 }
  );
}
```

戻り値が `null` ならアクセス可能、`NextResponse` ならそのまま返す。このパターンにより、APIルートの冒頭で1行のチェックを追加するだけで機能制限が実装できる。

## 認証・認可フロー

DevDexの認証は3層構造だ。

```
Layer 1: Supabase Auth（JWT発行・セッション管理）
Layer 2: checkAuth()（APIルートの認証チェック）
Layer 3: RLS（データベースレベルのアクセス制御）
```

`checkAuth()` は全APIルートの冒頭で呼び出される。

```typescript
export async function checkAuth(): Promise<AuthCheckResult> {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return {
      authenticated: false,
      response: NextResponse.json(
        { data: null, error: '認証が必要です' },
        { status: 401 }
      ),
    };
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single();

  return {
    authenticated: true,
    userId: user.id,
    role: (profile?.role as UserRole) ?? 'user',
  };
}
```

認証成功時に `userId` と `role` を返すことで、後続のFeature Gateチェックやデータ操作でそのまま使える。失敗時は `response` フィールドに401レスポンスが入るため、呼び出し側で即座に `return auth.response` できる。

## API設計パターン: { data, error }

DevDexの38本のAPIは、すべて同一のレスポンス形式に従う。

```typescript
// 成功
{ data: T, error: null }

// 失敗
{ data: null, error: string }
```

この形式を選んだ理由は3つある。

**1. クライアント側の型推論がシンプル**。`if (json.error)` で分岐するだけで、成功時のデータ型が確定する。

**2. HTTPステータスコードとの併用**。200番台は成功、400は入力エラー、401は未認証、403は権限不足、500はサーバーエラー。ステータスコードで大分類し、`error` フィールドで具体的なメッセージを返す。

**3. Implement Agentの一貫性**。パターンが1つに固定されているため、新しいAPIを追加するときもテンプレートのコピーで済む。38本のAPIすべてでレスポンス形式が統一されたのは、このパターンの効果だ。

## Claude Codeと設計ドキュメントの相互作用

DevDexのアーキテクチャは、Claude Code（特にPM Agent）との対話を通じて段階的に構築された。

典型的な流れは以下のとおりだ。

1. CLAUDE.mdにプロダクト概要と初期スキーマを書く
2. PM Agentが機能要件を読み、タスク分解と設計判断を `docs/decisions/` に記録する
3. Implement Agentが実装する。新しいテーブルが必要ならマイグレーションを追加
4. Review Agentが設計の整合性を確認する
5. 問題があればCLAUDE.mdを更新し、次のサイクルに反映する

この循環がDevDexのアーキテクチャを「進化」させた。001の初期スキーマ（terms、term_relations）から始まり、認証（003-006）、組織（008）、スキルシート（010）、診断（011-013）、AI概要補完（015）、権限（016）と、機能追加に合わせてスキーマが成長していく。

22本のマイグレーションは、開発の歴史そのものだ。各マイグレーションがどのフェーズのどのissueで追加されたかを追えば、DevDexがどう設計されたかの全貌が分かる。

PM Agentが `docs/decisions/` に記録した設計判断は、Implement Agentだけでなく将来の自分のための設計書でもある。「なぜ `term_relations` を配列でなく中間テーブルにしたのか」「なぜ `ai_overviews` を全ユーザー共有キャッシュにしたのか」。コードだけでは読み取れない意図が、設計ドキュメントとして残っている。

---

第10章では、DevDex開発全体の振り返り -- 数値で見る成果、AI駆動開発の課題と学び、そして今後の展望 -- を総括する。

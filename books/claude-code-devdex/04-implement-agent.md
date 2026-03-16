---
title: "Implement Agent: コード実装の自動化"
---

## Implement Agentの役割

Implement Agentは6体制の中で唯一「全ツールが使える」エージェントだ。

PM Agentが `docs/decisions/` に残した設計判断とタスク分解を読み、CLAUDE.mdの設計を参照しながら、コードを書き、テストを書き、コミットする。サブエージェント体制における「手を動かす担当」である。

DevDexの開発では、Implement Agentが63本のAPIエンドポイント、33画面、34本のDBマイグレーション、そして150のテストファイルに対する実装コードを出力した。

ただし、Implement Agentの仕事はコードを書くことだけではない。`format → lint → test → build` の4段階の品質チェックを通し、コミットメッセージを規約に沿って書き、GitHub Issueの作成からPRの作成までを一貫して行う。ここまでの一連の流れが「実装」だ。

## エージェント定義

```markdown
---
name: implement-agent
description: pm-agentのタスク分解を受けて実装を行う。
skills:
  - devdex-conventions
  - test-patterns
  - commit-style
---

あなたはこのプロジェクトの実装担当エンジニアです。

役割：
- docs/decisions/ の指示書に従って実装する
- CLAUDE.md の設計を必ず参照する
- 実装完了後 test-agent に引き渡す
```

PM Agentとの最大の違いは、`tools` フィールドがないことだ。ツール制限なし = 全ツール使用可能。Read、Write、Edit、Bash、Grep、Glob、WebFetch、WebSearchなど、Claude Codeが持つすべてのツールを使える。

もう1つの特徴は、3つのスキルが付与されている点だ。

| スキル | 内容 |
|---|---|
| `devdex-conventions` | TypeScriptルール、Supabase命名規則、コンポーネント設計方針 |
| `test-patterns` | Vitest 4の書き方、describe/itブロック、モックパターン |
| `commit-style` | `type: 日本語の説明` 形式のコミットメッセージ |

スキルはCLAUDE.md本体を肥大化させずに、ドメイン固有の知識をエージェントに注入する仕組みだ。`.claude/skills/devdex-conventions/skill.md` にはこのような内容が書かれている。

```markdown
## TypeScript
- `any` 禁止。unknown + 型ガードを使う
- `as` キャストは最終手段
- ES Modules（import/export）。CommonJSのrequire禁止

## APIルート（Next.js App Router）
- ファイル: src/app/api/[resource]/route.ts
- レスポンス: NextResponse.json({ data, error })
- エラー: 必ずtry-catchでハンドリング

## コンポーネント設計
- Server Components優先、必要な場合のみ 'use client'
- shadcn/ui + Tailwind CSSでスタイリング
- propsの型定義は必ずinterfaceで明示する
```

Implement Agentはこのスキルを読み込んだ状態でコードを書くため、レスポンス形式が `{ data, error }` で統一されたり、`any` の代わりに `unknown` + 型ガードが使われたりする。スキルが「コーディング規約の自動遵守」を実現する。

## 1 Issue = 1 Branch = 1 PR

Implement Agentの作業フローは厳格に定まっている。

```
1. docs/decisions/ の該当タスクを読む
2. GitHub Issue を作成する
3. feat/xxx ブランチを作成する
4. 実装する
5. format → lint → test → build を通す
6. コミットする
7. test-agent に引き渡す
```

この「1 Issue = 1 Branch = 1 PR」のルールは、CLAUDE.mdとMEMORYの両方に記載して厳守を徹底した。

```markdown
## GitHub運用ルール（厳守）
- **1 issue = 1 ブランチ = 1 PR**。mainに直接コミットしない
- ブランチ名: `feat/<機能名>` 形式
- 実装開始前に GitHub Issue を作成する
```

なぜここまで厳格にするのか。Claude Codeは指示がなければ効率を優先して、複数の変更を1つのコミットにまとめたり、mainに直接コミットしたりする。これを防ぐには、ルールを明文化してCLAUDE.mdに書くしかない。

DevDexでは520+件のPRがマージされた。すべてが1 Issue = 1 PRの原則を守っている。この一貫性がReview Agentのレビュー品質を支えた。レビュー対象が小さければ、見落としも少なくなる。

## 実装前の必須チェック: format / lint / test / build

Implement Agentがコミットする前に通す4段階の品質ゲートがある。

```bash
npm run format      # Prettierでフォーマット修正
npm run lint        # ESLint（エラー0であること）
npm run test:unit   # 全テストパス
npm run build       # プロダクションビルド成功
```

CLAUDE.mdに以下のように明記している。

```markdown
## コード変更後の必須チェック
コードを変更したら、**コミット前に必ず以下を実行**:
1. `npm run format` -- Prettierでフォーマット修正
2. `npm run lint` -- エラーが0であること（warningは許容）
3. `npm run test:unit` -- 全テストパス
4. `npm run build` -- ビルド成功
これらが全てパスしてからコミットすること。
```

さらに `.claude/settings.json` のフック設定で、ファイル書き込み時に自動チェックを走らせている。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "if [[ \"$CLAUDE_FILE_PATH\" == *.ts || \"$CLAUDE_FILE_PATH\" == *.tsx ]]; then npx tsc --noEmit 2>&1 | head -20; fi",
          "timeout": 30000
        }]
      },
      {
        "matcher": "Write(*.test.*)",
        "hooks": [{
          "type": "command",
          "command": "npm run test:unit 2>&1 | tail -15",
          "timeout": 60000
        }]
      }
    ]
  }
}
```

TypeScript/TSXファイルを書き込んだ直後に `tsc --noEmit` が走り、型エラーを即座に検出する。テストファイルを書き込んだ直後には `npm run test:unit` が走り、テストの成否をすぐに確認する。

このフックがあることで、Implement Agentは「書いて、エラーに気づいて、すぐ直す」というサイクルを自動で回せる。コミット時にまとめて4コマンドを実行する前に、大半のエラーが解消されている。

## APIルート設計パターン

DevDexの63本のAPIエンドポイントは、すべて同一のパターンで実装されている。PM Agentが定めた設計方針 -- Route Handlers + `{ data, error }` レスポンス -- をImplement Agentが忠実に適用した結果だ。

```typescript
import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { checkAuth } from '@/lib/auth';

/** GET /api/terms - 用語一覧取得 */
export async function GET(request: Request) {
  try {
    const auth = await checkAuth();
    if (!auth.authenticated) return auth.response;

    const supabase = await createClient();
    const { data, error } = await supabase.from('terms').select('*');

    if (error) {
      return NextResponse.json(
        { data: null, error: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ data, error: null });
  } catch {
    return NextResponse.json(
      { data: null, error: 'サーバーエラーが発生しました' },
      { status: 500 }
    );
  }
}
```

このパターンの特徴は3つある。

**1. checkAuth()による認証チェック**: すべてのAPIの冒頭で認証状態を確認する。未認証なら即座に401レスポンスを返す。

**2. 統一レスポンス形式**: 成功時は `{ data: T, error: null }`、失敗時は `{ data: null, error: string }`。クライアント側の型推論がシンプルになる。

**3. 二重のエラーハンドリング**: Supabaseのエラー（`if (error)`）と、それ以外の例外（`catch`）を分離。Supabaseのエラーメッセージはそのまま返し、予期しない例外は汎用メッセージで返す。

63本すべてがこのパターンに従っているため、新しいAPIを追加するときもテンプレートのコピーで済む。Implement Agentにとっても「このパターンに沿って書く」という明確な指針があるため、出力の一貫性が保たれた。

## 34マイグレーションの段階的な追加

DevDexのDBスキーマは34本のマイグレーションで段階的に構築された。

```
001_initial_schema.sql        -- terms, term_relations
002_dev_rls_policies.sql      -- 開発用RLSポリシー
003_profiles_and_user_role.sql -- profiles, user_role ENUM
004_terms_user_id.sql         -- terms.user_id 追加
005_terms_notes.sql           -- notes カラム追加
006_rls_policies.sql          -- 本番用RLSポリシー
007_profiles_username.sql     -- username カラム追加
008_organizations.sql         -- 組織関連テーブル群
009_ats_webhook_logs.sql      -- ATS Webhook ログ
010_skill_sheets.sql          -- スキルシートテーブル
011_engineer_diagnosis.sql    -- エンジニア診断
012_type_profiles.sql         -- タイププロファイル
013_profiles_diagnosis_mbti.sql -- MBTI連携
014_profiles_social_links.sql -- SNSリンク
015_ai_overviews.sql          -- AI概要補完
016_role_permissions.sql      -- 権限テーブル拡張
017_org_search_usage.sql      -- 組織検索利用量
018_terms_is_watched.sql      -- ウォッチリスト
019_terms_interview_prep.sql  -- 面談準備機能
020_stripe_columns.sql        -- Stripe連携カラム
021_diagnosis_demographics.sql -- 診断デモグラフィック
022_onboarding.sql            -- オンボーディング
```

マイグレーションの命名は連番（001〜022）で、ファイル名がそのまま変更内容を示す。001がtermsとterm_relationsの初期スキーマ、003でprofilesテーブルとuser_role ENUMが追加され、008で組織関連のテーブル群が一気に作られる。

この段階的なアプローチには理由がある。PM Agentのタスク分解がPhase単位で依存関係を定義しているため、各Phaseに対応するマイグレーションがそのタイミングで追加される。v0のPhase 1で001〜002、認証実装時に003〜006、v2で007〜009、v3で010〜019、という具合だ。

Implement Agentは新しいテーブルが必要になるたびに、連番の次の番号でマイグレーションファイルを作成する。この規約もCLAUDE.mdに暗黙的に含まれており、スキーマの変更履歴がそのまま追えるようになっている。

## Server Components優先の設計判断

DevDexのコンポーネント設計では、Server Components優先を徹底した。`'use client'` を付けるのは、以下の場合のみだ。

- フォーム入力（useState, useEffect を使うコンポーネント）
- インタラクティブUI（ドロップダウン、モーダル、タブ切り替え）
- クライアントサイドの状態管理が必要な場合

逆に、データの取得と表示だけのコンポーネントはServer Componentのまま。ページコンポーネント（`page.tsx`）は原則としてServer Componentで、データフェッチをサーバーサイドで行い、クライアントに渡す。

```
src/app/terms/page.tsx          -- Server Component（データ取得）
src/components/TermListTable.tsx -- 'use client'（フィルター・ソート操作）
src/components/TermForm.tsx      -- 'use client'（フォーム入力）
src/components/ui/Button.tsx     -- Server Component（表示のみ）
```

この方針はdevdex-conventionsスキルに「Server Components優先、必要な場合のみ 'use client'」と明記されているため、Implement Agentが自動的に遵守する。

## worktreeによる並列実行

PM Agentのv2タスク分解で「Phase A（並列）: v2-1, v2-3, v2-7, v2-9」という指示が出た場合、Implement Agentはgit worktreeを使って並列に実装できる。

```
devdex/
├── .claude/worktrees/
│   ├── agent-a7284ff6/   -- v2-1 レベルシステム
│   ├── agent-ac4f0920/   -- v2-3 username追加
│   └── agent-a382a338/   -- v2-7 PDFエクスポート
└── (メインワークツリー)   -- v2-9 GitHub OAuth
```

各worktreeは独立したブランチで作業するため、互いに干渉しない。Phase Aの4つのissueが完了したら、Phase Bのissueがそれぞれの成果を参照して実装を進める。

worktreeの活用は特に、DBスキーマの変更を含まないUI系のタスクで効果的だった。マイグレーションファイルの競合が起きないためだ。逆に、同じテーブルを変更する複数のissueでは並列実行を避け、直列で処理した。

## 自動許可オペレーション

`.claude/settings.json` の `permissions` セクションで、Implement Agentが確認なしで実行できるコマンドを定義している。

```json
{
  "permissions": {
    "allow": [
      "Read", "Edit", "Write", "Glob", "Grep",
      "Bash(npm run *)",
      "Bash(npm install*)",
      "Bash(npx tsc --noEmit*)",
      "Bash(npx shadcn@latest*)",
      "Bash(git log*)", "Bash(git diff*)", "Bash(git status*)",
      "Bash(git add*)", "Bash(git commit*)", "Bash(git push*)",
      "Bash(git checkout*)", "Bash(git branch*)"
    ],
    "deny": [
      "Bash(rm -rf*)",
      "Bash(git push --force*)",
      "Bash(git reset --hard*)",
      "Bash(git clean -f*)"
    ]
  }
}
```

`allow` リストに含まれるコマンドは、Implement Agentが人間の確認なしで実行する。`npm run format`、`npm run lint`、`npm run test:unit`、`npm run build`、git操作一式、shadcn/uiのコンポーネント追加など、日常的な開発コマンドがすべて含まれている。

一方で `deny` リストには破壊的な操作を明記した。`rm -rf`、`git push --force`、`git reset --hard`、`git clean -f` は、たとえImplement Agentが実行しようとしても拒否される。

この設定により、Implement Agentは「コードを書く → フォーマット → lint → テスト → ビルド → コミット → プッシュ」の全工程を、人間の介入なしで実行できる。1 issueあたりの実装が高速化された。

## Tips

### docs/decisions/が「仕様書」として機能する

Implement Agentが最初に読むのはCLAUDE.mdではなく `docs/decisions/` の該当ファイルだ。PM Agentが出力したタスク分解には、実装すべき内容（何を作るか）、採用した方針（どう作るか）、却下した選択肢（何をやらないか）が書いてある。

これがあることで、Implement Agentは「このAPIのレスポンス形式はどうすべきか」「Server Actionsを使うべきか」のような判断に迷わない。docs/decisions/が事実上の仕様書として機能する。

### テストは Test Agent に任せる

初期にImplement Agentがテストも一緒に書いてしまうパターンが頻発した。実装者がテストを書くと、自分のコードが正しい前提でテストを書くため、エッジケースの見落としが起きやすい。

対策として、Implement Agentの定義に「実装完了後 test-agent に引き渡す」と明記した。Implement Agentが書くのは実装コードのみ。テストはTest Agentの担当だ。

ただし、Implement Agentも `test-patterns` スキルを持っている。これは「テストを書くため」ではなく、「テストしやすいコードを書くため」だ。テストパターンを知っていれば、モックしにくい密結合な設計を避けられる。

### コミットメッセージの一貫性

`commit-style` スキルにより、Implement Agentのコミットメッセージは自動的に規約に従う。

```
feat: 用語登録フォームを実装する
fix: カテゴリフィルターのバグを修正
refactor: Supabaseクライアントの共通化
```

`type: 日本語の説明` の形式で、typeは `feat / fix / docs / refactor / chore / update` の6種類。全コミットがこの形式で統一されている。スキルの効果がもっとも分かりやすい例だ。

### フック設定の効果

`.claude/settings.json` のフック設定は、Implement Agentの生産性に大きく寄与した。TypeScriptファイルを書き込むたびに `tsc --noEmit` が自動実行されるため、型エラーを書いた直後に検出できる。テストファイルを書き込むたびに `npm run test:unit` が走るため、テストの成否をすぐに確認できる。

フックがない場合、Implement Agentは実装を全部書き終えてから `npm run build` を実行し、そこで大量の型エラーに直面して修正に時間がかかる。フックがあれば、エラーが小さいうちに修正できる。「早期発見・早期修正」の原則をシステムレベルで強制する仕組みだ。

---

Implement Agentがコードを書いたら、次はTest Agentの出番だ。第5章では「コードを編集できないテストエンジニア」が、2,100+件のテストをどう書いたかを解説する。

---
title: "プロンプト設計とCLAUDE.md"
---

## CLAUDE.mdはプロジェクトの「憲法」

サブエージェント6体制を支える最も重要なファイルが `CLAUDE.md` だ。

CLAUDE.mdはClaude Codeがセッション開始時に自動で読み込むプロジェクト設定ファイル。DevDexのCLAUDE.mdは約460行で、プロダクト概要、技術スタック、コーディング規約、DB設計、画面設計、収益化設計、サブエージェントフロー定義のすべてが詰まっている。

このファイルの役割は「プロジェクトの憲法」だ。6体のサブエージェントすべてがこのファイルを参照し、それぞれの役割に従って情報を読み取る。PM Agentはプロダクト概要と機能一覧を読んでタスクを分解し、Implement Agentは技術スタックとDB設計を読んでコードを書き、Review Agentはコーディング規約を読んでレビューする。

CLAUDE.mdに書かれていないことは、エージェントにとって「存在しない」。逆に書かれていることは、エージェントが自動的に遵守する。この性質を理解して、何を書き、何を書かないかを設計するのがプロンプト設計の本質だ。

## CLAUDE.mdの構成

DevDexのCLAUDE.mdは12のセクションで構成されている。

```markdown
# CLAUDE.md - IT用語理解度管理アプリ

## プロダクト概要（コンセプト・ターゲット・開発方針）
## 言語（コード: 英語、UI: 日本語、会話: 日本語）
## 技術スタック
## コマンド（npm run dev / build / lint / format / test:unit）
## コード変更後の必須チェック
## コミット規約
## ディレクトリ構成
## 自動許可オペレーション
## GitHub運用ルール（厳守）
## SubAgentsフロー
## Compact Instructions
## データベーススキーマ
## 画面設計
## 機能一覧（v0〜v3）
## ロール・権限設計
## 収益化設計
```

この構成は偶然の産物ではない。上から順に「なぜ作るか」「どう作るか」「何を作るか」の流れになっている。エージェントがファイルの先頭から読むことを意識した配置だ。

## 自動許可オペレーションの設計

Claude Codeはデフォルトでは、ファイルの編集やコマンドの実行のたびに人間の確認を求める。1日に数十回のコミットをするAI駆動開発では、この確認が深刻なボトルネックになる。

DevDexでは `.claude/settings.json` の `permissions` セクションで、日常的な操作を自動許可した。

```json
{
  "permissions": {
    "allow": [
      "Read", "Edit", "Write", "Glob", "Grep",
      "Bash(npm run *)",
      "Bash(npx tsc --noEmit*)",
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

設計の原則は「日常操作は許可、破壊的操作は拒否」だ。npm runコマンド、git操作、ファイルの読み書きは全て自動許可。一方で `rm -rf`、`git push --force`、`git reset --hard` は明示的に拒否リストに入れた。

さらにCLAUDE.md側にも自動許可の範囲を自然言語で記述している。

```markdown
## 自動許可オペレーション

以下の操作は確認なしで自動実行してよい:
- **参照系**: ファイル読み取り、Grep検索、Glob検索
- **Git操作系**: git add, git commit, git push, git pull
- **GitHub操作系**: gh issue create, gh pr create, gh pr merge
```

`settings.json` は機械的な制御、CLAUDE.mdは意図の伝達。両方を書くことで、エージェントが「何を自動でやっていいか」を正確に理解する。

## コミット規約とGit運用ルール

CLAUDE.mdで最も厳密に書いたセクションがGit運用ルールだ。

```markdown
## GitHub運用ルール（厳守）

- **1 issue = 1 ブランチ = 1 PR**。mainに直接コミットしない
- ブランチ名: `feat/<機能名>` 形式
- 実装開始前に GitHub Issue を作成する（labels: feat, v0, phase:xxx）
- PRは `gh pr create` で作成し、Issue をリンクする（`Closes #N`）
```

「厳守」と書いたのは意図的だ。Claude Codeは指示がなければ効率を優先して、mainに直接コミットしたり、複数の変更を1つのPRにまとめたりする。「厳守」の明記が、エージェントにこのルールの優先度を伝える。

コミット規約も同様にシンプルだが厳密に定義した。

```markdown
## コミット規約

- 形式: `type: 日本語の説明`
- type: `feat`, `fix`, `docs`, `refactor`, `chore`, `update`
- 例: `feat: 用語一覧画面を追加`
```

typeの種類を6つに限定し、説明は日本語という2つのルールだけ。シンプルだからこそ、全コミットで一貫性が保たれた。

## Skills: CLAUDE.mdを太らせない知識注入

CLAUDE.mdに全てを書くと肥大化する。DevDexでは3つのスキルファイルを `.claude/skills/` に分離した。

```
.claude/skills/
├── devdex-conventions/SKILL.md   # コーディング規約
├── test-patterns/SKILL.md        # テストの書き方
└── commit-style/SKILL.md         # コミットメッセージ規約
```

スキルファイルはエージェント定義の `skills:` フィールドで紐づける。

```markdown
---
name: implement-agent
skills:
  - devdex-conventions
  - test-patterns
  - commit-style
---
```

`devdex-conventions` スキルの中身を見てみよう。

```markdown
## TypeScript
- `any` 禁止。unknown + 型ガードを使う
- `as` キャストは最終手段

## APIルート（Next.js App Router）
- ファイル: src/app/api/[resource]/route.ts
- レスポンス: NextResponse.json({ data, error })

## コンポーネント設計
- Server Components優先、必要な場合のみ 'use client'
- shadcn/ui + Tailwind CSSでスタイリング
- propsの型定義は必ずinterfaceで明示する
```

これらのルールをCLAUDE.md本体に書くと、PM Agentやdiary Agentには不要な情報でコンテキストが消費される。スキルファイルに分離することで、必要なエージェントだけがスキルを読み込む。

エージェントごとのスキル割り当ては以下のとおりだ。

| スキル | PM | Implement | Test | Review | Diary |
|---|---|---|---|---|---|
| devdex-conventions | ○ | ○ | - | ○ | - |
| test-patterns | - | ○ | ○ | - | - |
| commit-style | - | ○ | - | - | - |

PM Agentに `devdex-conventions` を付けるのは、技術規約を理解した上でタスク分解するためだ。Implement Agentに `test-patterns` を付けるのは、テストしやすいコードを書くためであり、テストを書かせるためではない。各スキルの割り当てには明確な意図がある。

## ユーザーメモリ: MEMORY.md

CLAUDE.mdがプロジェクト単位の設定なら、MEMORY.mdはユーザー単位の永続記憶だ。`~/.claude/projects/<project>/memory/MEMORY.md` に配置され、セッションをまたいで保持される。

DevDexのMEMORY.mdには以下の情報を記録した。

```markdown
# DevDex プロジェクト メモリ

## 厳守ルール
### Git運用（絶対厳守）
- **1 issue = 1 ブランチ = 1 PR**。mainに直接コミットしない
- コミット前に format → lint → test → build を必ず通す
- ユーザーから厳守を指示されている。守れないなら設定を書き換えること

## 技術スタック
- Next.js 16 + TypeScript + Tailwind CSS v4 + shadcn/ui
- Supabase (ローカル: http://127.0.0.1:54321)

## 本番環境
- Vercel: https://devdex-app.vercel.app
- Admin: mt.oikawa@gmail.com / DevDex2026prod

## 開発状況
- v0〜v3実装完了: 45 API / 29ページ / 1,813テスト / 27マイグレーション
```

MEMORY.mdの最大の価値は、CLAUDE.mdに書ききれない「運用知識」を保持できることだ。本番環境のURL、テストユーザーの認証情報、Supabaseのアクセストークン。これらはプロジェクトの設計情報ではないが、開発作業には不可欠な情報だ。

もう1つ重要なのが「厳守ルール」の重複記載だ。CLAUDE.mdにもGit運用ルールは書いてあるが、MEMORY.mdにも「ユーザーから厳守を指示されている」と明記した。CLAUDE.mdはプロジェクトの全員が共有するファイルだが、MEMORY.mdは自分だけの記憶。二重に書くことで、エージェントがルールを軽視するリスクを下げている。

## Compact Instructions: 圧縮時の情報保持

長いセッションではClaude Codeがコンテキストを圧縮する。このとき何を保持し、何を捨てるかを指定するのが `Compact Instructions` セクションだ。

```markdown
## Compact Instructions

このセッションを要約するとき：

- 全APIの変更内容と選択理由を保持する
- エラーとその解決策を保持する
- 変更したファイル一覧を保持する
- 試みたが失敗したアプローチは簡潔に要約する
- Supabaseのテーブル構造は必ず保持する
- docs/decisions/の意思決定サマリーを保持する
```

この6項目を選んだ理由がある。

「全APIの変更内容と選択理由」は、Implement Agentが複数のAPIを実装する際に、前のAPIの設計判断を忘れると一貫性が崩れるためだ。「Supabaseのテーブル構造」は、DBスキーマの変更を伴う作業で直前のマイグレーション内容を忘れると二重定義が起きるため。

逆に「試みたが失敗したアプローチは簡潔に要約」という記述は、失敗の詳細を保持する必要はないが「やった」という事実は残す、というバランスだ。圧縮後に同じアプローチを再試行して時間を浪費するのを防ぐ。

## SubAgentsフローの記述

CLAUDE.mdの中でサブエージェントの全体像を定義するセクションがある。

```markdown
## SubAgentsフロー

新機能・修正・設計相談は以下の順で自動処理する：
PM Agent → Implement Agent → Test Agent → Review Agent

| エージェント    | 役割                 | 成果物                               |
| --------------- | -------------------- | ------------------------------------ |
| pm-agent        | 要件整理・意思決定記録 | docs/decisions/YYYY-MM-DD-[topic].md |
| implement-agent | 実装                 | コード変更                           |
| test-agent      | TDD・全件確認        | テスト結果                           |
| review-agent    | 品質・セキュリティ   | docs/review/YYYY-MM-DD.md           |
| diary-agent     | 日記生成             | docs/diary/YYYY-MM-DD.md            |
```

このテーブルの意味は「6体のエージェントが何を入力に取り、何を出力するか」の一覧表だ。CLAUDE.mdに書くことで、どのエージェントからでもフロー全体が参照できる。PM Agentがタスクを分解するとき、後続のTest AgentやReview Agentの存在を意識して「テストしやすい粒度」にタスクを切ることができる。

## Tips: CLAUDE.mdが大きくなりすぎたときの分割戦略

DevDexのCLAUDE.mdは約460行で、まだ管理可能な範囲だ。しかしプロジェクトが成長すると、CLAUDE.mdが1,000行を超えることもある。そうなるとエージェントのコンテキストを不要な情報が圧迫し、応答品質が下がる。

分割の戦略は3段階ある。

**段階1: スキルファイルへの分離**（DevDexで実施済み）

コーディング規約、テストパターン、コミット規約を `.claude/skills/` に分離する。CLAUDE.md本体は「何を作るか」に集中し、「どう書くか」はスキルに委譲する。

**段階2: セクション単位のファイル分割**

DB設計（`docs/design/db-schema.md`）、API設計（`docs/design/api-spec.md`）、画面設計（`docs/design/page-design.md`）を別ファイルに分離し、CLAUDE.mdにはファイルへの参照だけを残す。エージェントは必要に応じて該当ファイルを `Read` で読む。

**段階3: エージェント固有の追加コンテキスト**

`.claude/agents/pm-agent.md` のfrontmatterに `context:` フィールドを追加し、PM Agent固有の参照ファイルを指定する。エージェントごとに読むファイルが異なるため、全員が全情報を読む必要がなくなる。

DevDexでは段階1で十分だったが、v4以降で機能が増えるなら段階2への移行が必要になるだろう。分割のタイミングは「CLAUDE.mdを読むだけでコンテキストの半分以上が消費される」と感じたとき。それまでは1ファイルに集約するほうが管理しやすい。

## カスタムコマンドの活用

`.claude/commands/` にカスタムコマンドを配置すると、セッション開始時のオペレーションを定型化できる。DevDexでは3つのコマンドを用意した。

**`/start`**: PM Agentからタスク分解を開始する。新機能の開発セッションの起点。

**`/continue`**: 前回の続きから再開する。

```markdown
前回の続きから再開する。

1. docs/decisions/ と docs/diary/ の最新ファイルを読んで、
   前回どこまで進んだか把握する
2. 未完了のissueを確認して、次のissueから
   implement-agent で実装を再開する
3. セッション終了時は diary-agent で日記を生成する
```

`/continue` が特に有用だ。セッションが切れたとき、新しいセッションで `/continue` と入力するだけで、`docs/decisions/` と `docs/diary/` の最新ファイルを読み、中断地点を自動で特定して作業を再開する。ファイルシステム上のドキュメントがコンテキストの復元手段として機能する。

**`/diary`**: Diary Agentで1日の開発日記を生成する。

この3つのコマンドにより、「開発の開始」「中断からの復帰」「1日の締め」という3つのタイミングが定型化された。AI駆動開発のリズムを作る仕組みだ。

## CLAUDE.mdと設計ドキュメントの相互作用

DevDexの開発で最も効果的だったのは、CLAUDE.mdと `docs/decisions/` の相互作用だ。

CLAUDE.mdはプロジェクトの「あるべき姿」を定義する。`docs/decisions/` は「なぜそうしたか」を記録する。PM Agentが `docs/decisions/` に意思決定を書くとき、CLAUDE.mdの方針と整合しているかを確認する。Implement Agentが実装するとき、CLAUDE.mdの設計とdocs/decisions/の判断理由の両方を参照する。

この循環が品質を担保する。CLAUDE.mdが「Server Actionsは使わない」と書いてあり、docs/decisions/に「フォームと密結合しすぎる。将来モバイル対応時に再実装が必要になる」と理由が記録されている。3か月後にImplement Agentが新しいAPIを実装するとき、この2つの情報があれば同じ判断を維持できる。

プロンプト設計とは、結局「エージェントが正しい判断をするための情報環境を整える」ことだ。CLAUDE.md、スキルファイル、MEMORY.md、カスタムコマンド、settings.json。これらの設定ファイル群が組み合わさることで、6体のサブエージェントが一貫した方針でプロジェクトを前に進める基盤が出来上がる。

---

第9章では、DevDexのアーキテクチャ -- 技術選定の理由、DBスキーマの全体像、Feature Gate設計、認証・認可フロー -- を解説する。

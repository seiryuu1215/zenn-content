---
title: "サブエージェントフロー設計"
---

## なぜサブエージェントか？

### 1エージェントの限界

前作「ダーツラボ」では、Claude Codeと1対1のペアプログラミングで開発した。要件整理も実装もテストもレビューも、すべて1つのエージェントに任せていた。

これは小規模なアプリでは問題なかった。しかしDevDexの開発を始めて、あるポイントから品質が明らかに落ちた。

具体的に起きたのは「コンテキスト汚染」だ。

1つのエージェントに「PMとして要件を整理して」「実装して」「テストを書いて」「レビューして」と次々に役割を切り替えると、前の役割の思考が残ったまま次の作業に入る。テストを書くときに「自分が書いたコードだから正しいはず」という無意識のバイアスがかかる。レビューでも同様で、自分の実装を自分でレビューしても重大な見落としが生まれる。

さらに、1セッション内でのトークン消費が増え、後半になるほど応答品質が下がるという問題もあった。

### 役割分離がもたらす3つのメリット

1. **専門性の向上**: 各エージェントに「あなたはPMです」「あなたはQAエンジニアです」と明確な役割を与えることで、その視点に集中した出力が得られる
2. **品質ゲート**: PM → 実装 → テスト → レビューという直列パイプラインにより、各段階で品質チェックが入る。テストエージェントが全テストパスを確認しないとレビューに進めない
3. **コンテキストの最適化**: 各エージェントは自分の役割に必要な情報だけを読み込む。PM Agentはコードを読まないし、Review Agentはコードを書かない

## 6体制の全体設計

DevDexでは6つのサブエージェントを設計した。

| エージェント | 役割 | 成果物 |
|---|---|---|
| PM Agent | 要件整理・タスク分解・意思決定記録 | `docs/decisions/YYYY-MM-DD-[topic].md` |
| Implement Agent | コーディング・ファイル作成・修正 | コード変更 |
| Test Agent | TDD・テスト実行・全件パス確認 | テスト結果 |
| Review Agent | 品質・設計・セキュリティレビュー | `docs/review/YYYY-MM-DD.md` |
| Diary Agent | 開発日記生成・Zenn投稿素材 | `docs/diary/YYYY-MM-DD.md` |

### PM Agent

「あなたはこのプロジェクトのPMです。実装はしません。」

PM Agentの最大の特徴は**コードを書かない**こと。使えるツールを`Read`と`Glob`だけに制限している。コードが書けないからこそ、要件整理と設計判断に集中できる。

PM Agentの成果物は`docs/decisions/`配下の意思決定記録だ。DevDexでは20件の意思決定記録が残っている。各記録には統一フォーマットがある。

```markdown
## 背景・課題
## 採用した方針
## 却下した選択肢
| 選択肢 | 却下理由 |
## タスク分解
- [ ] タスク1（工数見積もり）
```

このフォーマットの中で特に重要なのが「却下した選択肢」セクションだ。なぜ他のアプローチを選ばなかったのかを明記することで、後から「なぜこうなっているのか」を振り返れる。たとえばDevDexでは「Server Actionsを使わずRoute HandlersでCRUD APIを構築する」という判断があり、その理由は「フォームと密結合しすぎる。将来モバイル対応時に再実装が必要になる」と記録されている。

### Implement Agent

「あなたはこのプロジェクトの実装担当エンジニアです。」

Implement Agentは`docs/decisions/`の指示書に従って実装する。PM Agentが「何を作るか」を決め、Implement Agentが「どう作るか」を実行する。ツール制限はなく、全ツールを使用可能だ。

3つのスキル（`devdex-conventions`、`test-patterns`、`commit-style`）を付与しており、コーディング規約・テストパターン・コミットメッセージの形式を自動的に遵守する。

### Test Agent

「あなたはこのプロジェクトのQAエンジニアです。」

Test Agentの使えるツールは`Read`、`Bash`、`Glob`の3つ。コードの**編集はできない**が、テストファイルの**作成と実行はできる**。実装コードに手を加えずにテストを書くことで、「テストを通すためにテスト側を妥協する」事態を防いでいる。

テスト結果（件数・Pass/Fail・気づき）は`docs/diary/YYYY-MM-DD.md`に追記される。

### Review Agent

「あなたはこのプロジェクトのシニアレビュアーです。」

Review Agentの使えるツールは`Read`、`Glob`、`Grep`の3つ。読み取り専用だ。コードを変更する権限がないため、純粋にレビューに集中する。

レビュー結果は`docs/review/YYYY-MM-DD.md`に指摘事項・承認理由とともに記録される。指摘にはカテゴリ（naming/security/performance/design）と重要度（Critical/Warning/Info）が付く。

### Diary Agent

「あなたはこのプロジェクトの記録担当です。実装はしません。」

1日の作業終了時に呼び出すエージェント。`docs/decisions/`、`docs/review/`、テスト結果、`docs/logs/`のログを統合して開発日記を生成する。末尾にZenn投稿用サマリー（200字）を追記する。使えるツールは`Read`と`Glob`のみ。

## フロー図

基本のフローは直列パイプラインだ。

```
ユーザーの要望
    |
    v
[PM Agent] ---- docs/decisions/*.md を出力
    |
    v
[Implement Agent] ---- コード変更
    |
    v
[Test Agent] ---- テスト実行・結果記録
    |   |
    |   +-- 失敗 --> [Implement Agent] に差し戻し
    |
    v
[Review Agent] ---- docs/review/*.md を出力
    |   |
    |   +-- Critical指摘 --> [Implement Agent] に差し戻し
    |
    v
PR作成・マージ
    |
    v
[Diary Agent] ---- docs/diary/*.md にエントリ追記
```

各エージェントの入出力を整理すると以下のようになる。

| エージェント | 入力 | 出力 |
|---|---|---|
| PM Agent | ユーザーの要望、CLAUDE.md | `docs/decisions/*.md`（タスク分解・設計判断） |
| Implement Agent | `docs/decisions/*.md`、CLAUDE.md | コード変更、コミット |
| Test Agent | 変更されたコード | テスト結果、`docs/diary/*.md`への追記 |
| Review Agent | 変更されたコード、diff | `docs/review/*.md`（指摘事項） |
| Diary Agent | decisions、review、logs、テスト結果 | `docs/diary/*.md`（統合日記） |

ここで重要なのは、エージェント間の受け渡しが**ファイルシステム上のドキュメント**で行われる点だ。PM Agentが`docs/decisions/`に書いた意思決定記録を、Implement Agentが読んで実装する。メモリ上の状態ではなくファイルとして残るため、セッションが切れても情報が失われない。

## CLAUDE.mdでの設定方法

サブエージェントの定義は2箇所に記述する。

### 1. CLAUDE.md内のSubAgentsフローセクション

```markdown
## SubAgentsフロー

新機能・修正・設計相談は以下の順で自動処理する：
PM Agent → Implement Agent → Test Agent → Review Agent

| エージェント    | 役割                 | 成果物                               |
| --------------- | -------------------- | ------------------------------------ |
| pm-agent        | 要件整理・意思決定記録 | docs/decisions/YYYY-MM-DD-[topic].md |
| implement-agent | 実装                 | コード変更                           |
| test-agent      | TDD・全件確認        | テスト結果                           |
| review-agent    | 品質・設計・セキュリティ | docs/review/YYYY-MM-DD.md         |
| diary-agent     | 日記生成・Zennサマリー | docs/diary/YYYY-MM-DD.md           |
```

CLAUDE.mdに書くことで、どのエージェントからでもフロー全体が見える。これが「Single Source of Truth」として機能する。

### 2. `.claude/agents/`配下のエージェント定義

各エージェントの詳細定義は`.claude/agents/`ディレクトリに個別のMarkdownファイルとして配置する。

```
.claude/
├── agents/
│   ├── pm-agent.md
│   ├── implement-agent.md
│   ├── test-agent.md
│   ├── review-agent.md
│   └── diary-agent.md
├── commands/
│   ├── start.md      # 開発開始コマンド
│   ├── continue.md   # 前回の続きから再開
│   └── diary.md      # 日記生成
├── skills/
│   ├── devdex-conventions/  # コーディング規約
│   ├── test-patterns/       # テストの書き方
│   └── commit-style/        # コミットメッセージ規約
└── settings.json            # 権限・フック定義
```

エージェント定義の例として、PM Agentのファイルを示す。

```markdown
---
name: pm-agent
description: ユーザーの要望を受けて要件整理・タスク分解・意思決定の記録を行う。
tools: Read, Glob
skills:
  - devdex-conventions
---

あなたはこのプロジェクトのPMです。実装はしません。

役割：
- ユーザーの要望を聞いてタスクに分解する
- 実装方針・技術選定の意思決定を記録する
- 作業結果を docs/decisions/YYYY-MM-DD-[topic].md に保存する
- 完了後 implement-agent に引き渡す

制約：コードを書かない / docs/decisions/ 以外のファイルを変更しない
```

frontmatterの`tools`フィールドでツール制限を設定するのが肝心だ。PM AgentやReview Agentがコードを書けないようにすることで、役割の境界を強制する。

### 3. Hooks: 自動品質チェック

`.claude/settings.json`にフック定義を記述する。DevDexでは以下の3つのフックを設定した。

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "npx tsc --noEmit 2>&1 | head -20",
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

- **TypeScriptコンパイルチェック**: `.ts`/`.tsx`ファイルを書き込んだ直後に`tsc --noEmit`を実行。型エラーを即座に検出する
- **テスト自動実行**: テストファイルを書き込んだ直後に`npm run test:unit`を実行。書いたテストがすぐに通るか確認する
- **ログ記録**: 全ツール実行をJSONLファイルに記録し、後でDiary Agentが参照する

これらのフックにより、Implement Agentが型エラーのあるコードをコミットする前に問題が検出される。

## 1 Issue = 1 Branch = 1 PRの厳守

サブエージェントフローと同じくらい重要なルールが「1 Issue = 1 Branch = 1 PR」だ。CLAUDE.mdとMEMORYの両方に記載し、厳守を徹底した。

```markdown
## GitHub運用ルール（厳守）
- **1 issue = 1 ブランチ = 1 PR**。mainに直接コミットしない
- ブランチ名: `feat/<機能名>` 形式
- 実装開始前に GitHub Issue を作成する
```

このルールにはサブエージェントフローとの相性がよい理由がある。

PM Agentがタスクを分解するとき、各タスクは「1〜2時間で終わる粒度」に収める。この1タスク = 1 Issue = 1 PR = 1サブエージェントフロー1周という単位が、開発のリズムを作る。DevDexのv0ではPM Agentが14個のissueに分解し、それぞれが1つのPRとしてマージされた。

もしこのルールがなければ、1つの巨大PRに複数の機能変更が混在し、Review Agentのレビュー品質が下がる。差し戻しが発生したときの修正範囲も広がる。小さく分割して小さく回すのが、AI駆動開発でもっとも重要な原則だ。

## 実績データ

DevDexの開発を通じた実際の数値を示す。

### PM Agentの成果

`docs/decisions/`に20件の意思決定記録。v0のタスク分解（14 issue、18.5時間見積もり）、v1（7 issue、9時間）、v2（10 issue、15.5時間）と段階的に計画を作成した。

v0のタスク分解の例を示す。

```
Phase 1: 基盤（データ層）  → 2 issue
Phase 2: コアUI            → 4 issue
Phase 3: インタラクション  → 4 issue
Phase 4: ダッシュボード    → 1 issue
Phase 5: AI機能            → 2 issue
Phase 6: 認証              → 1 issue
```

依存関係図も同時に出力させたことで、Implement Agentが「次に何を実装すべきか」を迷わなくなった。

### Test Agentの成果

- ユニットテストファイル: 118ファイル
- テスト数: 1,813件（v0: 403件 → v1完了: 496件 → v3完了: 1,316件 → 公開準備: 1,407件 → 機能追加: 1,813件）
- テストカバレッジ: API Route、ユーティリティ関数、コンポーネントを網羅

### Review Agentの成果

`docs/review/`にレビュー記録を蓄積。指摘はカテゴリ（security/design/performance/naming）と重要度（Critical/Warning/Info）で分類される。実際のレビュー結果の例を示す。

```markdown
## 総合結果: 承認
Critical な指摘なし。Warning 3件は現フェーズで許容範囲。

| # | カテゴリ   | 内容                                        | 重要度  |
|---|-----------|---------------------------------------------|---------|
| 1 | security  | 未検証の typeCode を画像パスに直接使用        | Warning |
| 2 | performance | 全用語取得して案件ごとに個別API呼び出し     | Warning |
| 3 | design    | 候補者検索APIで diagnosis が常に null        | Warning |
```

### 全体の実装速度

- 総PR数: 460件超（マージ済み）
- v0 MVP: 14 issue、実働3〜4日
- 1 issue あたりの平均: 1〜2時間

## Tips とハマりポイント

### エージェント間のコンテキスト受け渡し

サブエージェント間でコンテキストを渡す方法は「ファイルシステム経由」が基本だ。PM Agentが`docs/decisions/`に書いた内容を、Implement Agentが読む。メモリ上のやり取りに頼らない。

これに加えて、CLAUDE.mdの「Compact Instructions」セクションが重要になる。Claude Codeがセッションを要約するとき、何を保持すべきかを指定しておく。

```markdown
## Compact Instructions
このセッションを要約するとき：
- 全APIの変更内容と選択理由を保持する
- エラーとその解決策を保持する
- 変更したファイル一覧を保持する
- Supabaseのテーブル構造は必ず保持する
- docs/decisions/の意思決定サマリーを保持する
```

これにより、長時間のセッションでコンテキストが圧縮されても、重要な情報が失われにくくなる。

### カスタムコマンドの活用

`.claude/commands/`にカスタムコマンドを定義しておくと、セッション開始時の手間が減る。DevDexでは3つのコマンドを用意した。

- `/start`: PM Agentからv0のタスク分解を開始する
- `/continue`: 前回の`docs/decisions/`と`docs/diary/`を読んで、中断した場所から再開する
- `/diary`: Diary Agentで1日の日記を生成する

特に`/continue`コマンドは、セッションが切れたときの復帰に効果的だ。`docs/decisions/`と`docs/diary/`の最新ファイルを読むだけで、プロジェクトの現在地が分かる。

### スキルの使い分け

`.claude/skills/`にスキル定義を配置し、エージェントごとに必要なスキルだけを付与する。

| スキル | PM Agent | Implement Agent | Test Agent | Review Agent |
|---|---|---|---|---|
| devdex-conventions | ○ | ○ | - | ○ |
| test-patterns | - | ○ | ○ | - |
| commit-style | - | ○ | - | - |

スキルはCLAUDE.md本体を肥大化させずに、ドメイン固有の知識をエージェントに注入する手段だ。コーディング規約（TypeScriptのルール、Supabaseの命名規則）やテストパターン（Vitest + Testing Library の書き方）を独立したファイルとして管理できる。

### トークン消費の最適化

サブエージェント6体制はトークン消費が増えるように見えるが、実際にはコンテキスト汚染による「やり直し」が減るため、トータルでは効率的だった。

最適化のポイントは以下の3つ。

1. **ツール制限による読み込み抑制**: PM Agentは`Read`と`Glob`しか使えないので、不要なコードを読み込まない
2. **成果物のドキュメント化**: エージェント間の受け渡しをファイル経由にすることで、必要な情報だけを次のエージェントが読む
3. **1 issue = 1 PRの粒度**: 各サブエージェントフロー1周の範囲が小さいため、1周あたりのトークン消費が制限される

### ハマりポイント: エージェントの役割逸脱

初期にハマったのは、Implement Agentが「テストも一緒に書いてしまう」パターンだ。実装者がテストを書くとテストの品質が甘くなりがちで、本来Test Agentが担うべき観点が抜ける。

対策として、Implement Agentの定義に「実装完了後 test-agent に引き渡す」と明記し、テスト作成はTest Agentに任せるフローを徹底した。

もう1つのハマりポイントは、PM Agentのタスク分解が粗すぎるケース。「スキルシート機能を実装する」のような大きなタスクだと、Implement Agentが方向を見失う。PM Agentには「1 issue = 1〜2時間で終わる粒度」をルールとして課し、大きな機能は複数issueに分解させた。実際、スキルシート機能は7つのissue（DBスキーマ → CRUD API → 経歴書タブ → スキル一覧タブ → 個人開発タブ → PDF/Excelエクスポート → 公開ページ）に分解された。

---

次章からは、各エージェントの詳細に踏み込む。第3章ではPM Agentのプロンプト設計と、意思決定記録の実例を深掘りする。

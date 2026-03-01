---
title: "Firestore 23コレクションの設計判断"
---

## RDB 脳を捨てるところから始まった

Firestore は NoSQL だ。RDB の正規化ルールをそのまま持ち込むと痛い目を見る。darts Lab の Firestore 設計は「12のルートコレクション + 11のサブコレクション = 計23コレクション」という構成になった。

```
Firestore Root
├── users/{userId}           ← 11のサブコレクションを持つ
├── darts/{dartId}
├── articles/{articleId}
├── discussions/{discussionId}
├── barrels/{barrelId}
├── barrelRanking/{rankId}
├── comments/{commentId}
├── stripeEvents/{eventId}
├── lineConversations/{id}
├── lineLinkCodes/{code}
├── config/{configId}
└── reports/{reportId}
```

最初は機能を絞っていたのでコレクション数はもっと少なかった。ただ Claude Code を使うと実装が簡単にできてしまうため、機能もコレクションも増えがちだった。途中から「本当に必要な機能か？」「ユーザーに求められているものは何か？」を常に自問し、不要なものは削るようにした。AI駆動開発では「作れてしまう」ことがスコープ膨張のリスクになる。

## サブコレクションにした理由

`users/{userId}` の下に11のサブコレクションがぶら下がっている。

```
users/{userId}
├── dartsLiveStats/{docId}     スタッツ履歴
├── dartsliveCache/latest      最新スタッツのキャッシュ
├── barrelBookmarks/{barrelId} バレルブックマーク
├── dartBookmarks/{dartId}     セッティングブックマーク
├── dartLikes/{dartId}         いいね
├── shopBookmarks/{bookmarkId} ショップブックマーク
├── shopLists/{listId}         ショップリスト
├── goals/{goalId}             目標
├── notifications/{id}         通知
├── xpHistory/{xpId}           XP獲得履歴
└── settingHistory/{historyId} セッティング変更履歴
```

なぜルートコレクションではなくサブコレクションにしたのか。理由は3つある。

**1. セキュリティルールが自然に書ける。** サブコレクションなら `match /users/{userId}/goals/{goalId}` でパスから所有者が自明になる。ルートコレクションだと毎回 `resource.data.userId == request.auth.uid` を書く必要がある。

**2. クエリのスコープが絞られる。** `users/{uid}/dartsLiveStats` をクエリすれば自分のデータだけが返る。ルートコレクションだと全ユーザーのデータから `where('userId', '==', uid)` でフィルタする必要がある。

**3. 削除が容易。** ユーザー退会時にサブコレクションごと削除できる。

一方、 `darts` や `articles` や `discussions` はルートコレクションにした。これらは**他のユーザーが閲覧する**データだからだ。サブコレクションにすると、一覧取得で全ユーザーのサブコレクションを横断する Collection Group Query が必要になり、パフォーマンスとセキュリティルールの複雑さが跳ね上がる。

## 戦略的な非正規化

Firestore には JOIN がない。愚直に正規化すると、1つの画面を表示するために何回もドキュメントを読むことになる。darts Lab では **ユーザー名とアバターURL** を各ドキュメントに埋め込む非正規化を採用した。

```typescript
// darts コレクション — userName, userAvatarUrl を埋め込み
{
  userId: "abc123",
  userName: "青竜",        // ← users/{userId}.displayName のコピー
  userAvatarUrl: "https://...",  // ← users/{userId}.avatarUrl のコピー
  title: "トルピード系セッティング",
  barrel: { name: "RISING SUN", ... },
  ...
}
```

`comments`, `discussions`, `replies`, `articles` にも同じパターンで埋め込んでいる。これにより、セッティング一覧やコメント一覧を表示するときに **1回のクエリ** で完結する。

トレードオフは「ユーザーがプロフィールを更新したとき、全ドキュメントを書き換える必要がある」こと。ただ、プロフィール変更の頻度は低い（月に1回もない）のに対して、一覧表示は毎日何十回も発生する。読み取り頻度と書き込み頻度のバランスを考えれば、非正規化が圧倒的に合理的だった。

実際にデータ不整合に近いバグは経験した。ユーザーのプレイログを取得する際に、本日分のスタッツが常に0になる問題が発生した。調べてみると、DARTSLIVE の API 仕様としてデータが反映されるのは JST 6時であり、「本日分」ではなく「昨日分」が最新だった。非正規化とは別の問題だが、外部データソースのタイミングとキャッシュの整合性は意識する必要があると学んだ。

## dartsliveCache/latest — サブ1秒ロードの仕組み

スタッツダッシュボードのトップに表示されるレーティングやフライト情報は、`users/{uid}/dartsliveCache/latest` という **単一ドキュメント** から取得している。

```typescript
// dartsliveCache/latest の構造
{
  rating: 10.4,
  ratingInt: 10,
  flight: "BB",
  cardName: "カード名",
  stats01Avg: 23.45,
  statsCriAvg: 2.1,
  statsPraAvg: 521.3,
  prevRating: 10.2,       // ← 前回値も保持
  prevStats01Avg: 22.25,
  updatedAt: Timestamp
}
```

なぜこのキャッシュが必要なのか。DARTSLIVE のデータ取得はブラウザ自動化経由で **30〜60秒** かかる。毎回トップページを開くたびにこの待ち時間が発生したら、サービスとして成り立たない。

そこで、データ取得が成功したタイミングで `dartsliveCache/latest` に最新値を書き込み、ダッシュボードはこのキャッシュからサブ1秒で表示する。直前の値（`prevRating` 等）も一緒に保持しているので、前回比の上下矢印もキャッシュだけで描画できる。

## セキュリティルールが最後の砦

Firestore セキュリティルールは「あったらいいな」ではなく、**本番環境のアクセス制御そのもの** だ。darts Lab のルールで特に重要なのが **ロール昇格防止** のルールだ。

```javascript
// firestore.rules — users ドキュメントの更新制限
allow update: if isAdmin()
  || (isOwner(userId)
      && !request.resource.data.diff(resource.data).affectedKeys()
          .hasAny(['role', 'stripeCustomerId', 'subscriptionId',
                   'subscriptionStatus', 'subscriptionCurrentPeriodEnd',
                   'subscriptionTrialEnd', 'xp', 'level', 'rank', 'achievements']));
```

`diff().affectedKeys()` で「変更されたフィールド」を検出し、`role` や `subscriptionId` などの機密フィールドが含まれていたら拒否する。つまり、**クライアントから直接 Firestore SDK でロールを書き換える攻撃を、ルールレベルでブロック** している。

ロール変更は Admin SDK 経由（つまりサーバーサイド）でしか実行できない。セキュリティルールは Admin SDK をバイパスするので、Webhook やAPIからの正規の変更は通る。

他にも、セキュリティルールの設計判断として重要なポイントがある。

| コレクション | ルール | 理由 |
|-------------|--------|------|
| `dartsliveCache` | `allow read, write: if false` | Admin SDK 限定。クライアントからの読み書きを完全遮断 |
| `stripeEvents` | `allow read, write: if false` | 決済イベントの改ざん防止 |
| `barrels` | `allow read: if true; allow write: if false` | 読み取り専用。インポートは Admin SDK |
| `xpHistory` | `allow read: if isOwner; allow write: if false` | XP改ざん防止。付与はサーバー側のみ |

「クライアントには読ませるが書かせない」「クライアントからは完全に遮断」というパターンを使い分けることで、フロントエンドが乗っ取られてもデータの整合性を保てる設計になっている。

セキュリティルールについては、基本的に入力項目を絞ることにフォーカスしていた。AI がいい感じに補完してくれることが多く、個人開発では助かったが、実務ではもっと厳密に見るべきだとも感じた。個人開発という性質上、まず成果物の全体的なレベルを上げることを優先し、あとからコードレビューとセキュリティレビューを AI に実施させることでカバーする方針を取った。

次章では、こうした設計を Claude Code と一緒にどう実装していったか、AI とペアプロする日常について書いていく。

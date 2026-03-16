---
title: "IT初心者でもわかるサブスク決済の裏側 — Stripeで課金機能を実装した話"
emoji: "💳"
type: "tech"
topics: ["stripe", "webhook", "nextjs", "初心者向け"]
published: false
---

## サブスク決済の裏側で何が起きているか

NetflixやSpotifyのような月額課金サービス。「クレジットカードを登録して、毎月自動で引き落とし」という体験の裏側では、複雑な処理が動いている。

darts Lab では **Stripe** という決済プラットフォームを使って、PRO プラン（月額サブスクリプション）を実装した。

## Stripeとは？

Stripe は開発者向けの決済サービスだ。最大のメリットは **クレジットカード情報を自分のサーバーで持たなくていい** こと。

カード情報の管理には PCI DSS という厳格なセキュリティ基準への準拠が必要で、個人開発者が対応するのは現実的ではない。Stripe が代わりに管理してくれるので、開発者は「決済を開始する」「結果を受け取る」だけで済む。

## 決済フロー — 5ステップで PRO になる

```
① ユーザーが「PROにアップグレード」ボタンをクリック
    ↓
② Stripe Checkout（Stripeが用意した決済画面）に遷移
    ↓
③ カード情報を入力して決済完了
    ↓
④ Stripe が Webhook で「決済完了」をサーバーに通知
    ↓
⑤ サーバーが Firestore の role を 'general' → 'pro' に更新
```

ポイントは **④ の Webhook** だ。

## Webhook — 「終わったら電話して」方式

Webhookは「イベントが発生したら、指定したURLに通知する」仕組みだ。

| 方式 | 比喩 | 特徴 |
|------|------|------|
| ポーリング | 「まだですか？」と何度も電話する | サーバー負荷が高い、タイムラグがある |
| **Webhook** | 「終わったら折り返し電話して」と伝える | 効率的、リアルタイム |

Stripe は決済に関するイベントが発生すると、サーバーの `/api/stripe/webhook` に POST リクエストを送ってくる。darts Lab では4種類のイベントを処理している。

| イベント | 何が起きたか | アプリの処理 |
|---------|------------|------------|
| `checkout.session.completed` | 決済成功 | role を 'pro' に昇格 |
| `customer.subscription.updated` | プラン変更 | ステータスを同期 |
| `customer.subscription.deleted` | 解約 | role を 'general' に戻す |
| `invoice.payment_failed` | 支払い失敗 | ステータスを 'past_due' に |

## 冪等性 — 同じ処理を何回やっても結果が同じ

ネットワークが不安定だと、Stripe は **同じイベントを複数回送ってくる** ことがある（公式ドキュメントにも明記されている）。

もし対策しないと、同じユーザーが二重に PRO 化されたり、ダウングレードが二重実行されたりする可能性がある。

```typescript
// stripeEvents コレクションで処理済みチェック
const eventDoc = await eventRef.get();
if (eventDoc.exists) {
  // すでに処理済み → 何もしないで200を返す
  return NextResponse.json({ received: true });
}
// 処理を実行した後、イベントIDを記録
await eventRef.set({ type: event.type, processedAt: Timestamp.now() });
```

イベントIDで「処理済みかどうか」を記録しておくことで、何回同じイベントが来ても安全に処理できる。これが **冪等性**（べきとうせい）だ。

## 署名検証 — 本物のStripeからの通知か確認する

Webhook のURLは公開されている。悪意のある第三者が偽のWebhookを送ってきたら？「決済完了」の偽通知で、無料ユーザーがPROになってしまう。

これを防ぐため、Stripe は各リクエストに **署名** を付けている。サーバー側では `stripe.webhooks.constructEvent()` で署名を検証し、本物のStripeからの通知であることを確認する。

## まとめ

- Stripe を使えば、カード情報を自分で管理せずに決済機能を実装できる
- Webhook で「決済完了」などのイベントをリアルタイムに受け取る
- 冪等性で二重処理を防止
- 署名検証で偽のWebhookをブロック

次の記事では、毎朝自動でデータを取得して LINE で通知する仕組みを解説する。

---

*この記事は darts Lab（90,000行のダーツスタッツ管理アプリ）の実装を元に解説しています。*

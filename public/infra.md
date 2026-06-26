---
title: インフラについて - Nercone
extra_imports: <link rel="stylesheet" href="/assets/css/pages/infra.css">
---

<div class="hero">
    <h1>インフラについて</h1>
    <p>最終更新: 2026/06/27 2:26 JST</p>
</div>

<div class="limited-width">

<img src="/assets/images/other/infra.webp" class="border">

このページではnercone.devの構成について紹介します。

## ノードについて
nercone.devは複数のノードで構成されています。

CentralノードはGCP Compute Engine上のVMで、メールサーバー以外のサーバーを実行させています。

Mailノード(XServerノードとも呼んでいます)はXServer VPS上のVMで、メールサーバーを実行させています。

## メールサーバーを分離している理由
メールサーバーを分離しているのには理由があります。

GCPを含む主要なクラウドサービスは、スパム防止のために上りのSMTP接続(正確には`25/tcp`での接続)をブロックします。
つまり、Centralノードはメールの送信ができません。

そのため、メールサーバーはCentralノード以外の場所に配置する必要があります。

SMTP接続の制限がない...となると、VPSサービス(XServer VPSやConoHa VPSなど)がちょうどよく感じます。

そういうわけで、メールサーバーはXServer VPSに分けています。
制限が解除され次第、Centralノードに移動する予定です。

## 課題
個人サイトとしては十分だと思いますが、どうしても冗長化したい気持ちがあります。

...やりませんよ？面倒なので。

</div>

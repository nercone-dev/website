---
title: サーバーについて - Nercone
header_desc: このサーバーの詳細情報
description: nercone.devのサーバーの詳細情報
---

# nercone.dev ({{ repository.version }})
nercone.devへのHTTP(S)リクエストは、Python+Hypercorn+FastAPIで構築されたWebサーバーによって処理されています。

サードパーティのソフトウェアや機密情報などの公開ができない/難しい箇所を除く、ほとんどの箇所はGitHubで公開しています。

### HTTP
HTTP/1.1/2/3(QUIC)に対応しています。

### TLS
HypercornでTLSに対応しています。

SSLの全バージョンを含む、TLS 1.1以前のSSL/TLSは無効化しています。TLS 1.2/1.3でのみアクセス可能です。

証明書はCertbotを使用してLet's Encrypt様に発行してもらっています。プロファイルはtlsserverです。

### PQC (ポスト量子暗号)
`X25519MLKEM768`などのハイブリッドPQCでの鍵交換に対応済みです。
純粋なPQC(`MLKEM1024`/`MLKEM768`)にも対応済みですが、ハイブリッドPQCより優先順位を低くしています。

## リポジトリ ([github.com:nercone-dev/website](https://github.com/nercone-dev/website/)@[{{ repository.version }}]({{ "https://github.com/nercone-dev/website/commit/" + repository.version }}))
途中でGiteaに移動したり戻したり~~ラジバンダリ~~しましたが、現時点でサーバーのソースコードはここで管理しています。
やっぱりGitHubが一番落ち着くんです。

## その他の情報

### レジストラ
以前までお名前.comを使用していましたが、Cloudflareに移管しました。

### DNSサーバー
ドメイン移管前からCloudflareを使用しています。

### サーバー(物理)
GCPのCompute Engineを使用しています。マシンタイプはe2-mediumです。

リージョンはasia-northeast2 (大阪)です。
日本なのでレイテンシが低く、かつ東京より安いためです。

LinuxディストリビューションはAlmaLinux 10.2を使用しています。

### メールサーバー
GCPだと上りの25/tcpポートがスパム対策かなんかでブロックされるので、メールだけ別で用意したXServerのVPSで処理させています。

ソフトウェアはPostfix+Dovecotの設定が面倒なのでPoste.ioに任せています。いつか移行予定です。

### 今年
今年は西暦で{{ this_year }}年、つまり平成{{ this_year_in_heisei }}年です。時の流れは速いですねぇ。

えっ？何？令和？なんですかそれ。聞いたことありませんね。ネーミングセンスの良い和菓子でしょうか...？今度1つ買ってきてくださいよ。

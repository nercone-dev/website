# CLAUDE.md
このファイルは、Claude Codeがこのリポジトリ内のコードを扱う際に知っておくべき情報を提供するものです。

## 概要
ここは[nercone.dev](https://nercone.dev/)のソースコードを管理するリポジトリです。

`nercone_dev` トップレベルパッケージの下に機能ごとのサブパッケージを配置する構成です。現在は`website`サブパッケージのみが存在します。

- `website`: Python 3.12のFastAPI + Hypercornの上で動くASGIアプリケーション

## ファイル構造

### リポジトリルート (`/`)

```
https://github.com/nercone-dev/website.git
├── databases
│   ├── .gitkeep
│   ├── access_counter.txt       # アクセスカウンタ (整数テキスト)
│   └── mime.types               # Apache httpd から30日毎に自動取得するMIMEタイプ定義
├── logs
│   ├── .gitkeep
│   ├── app.log                  # 一般ログ (Logger.log)
│   ├── access.log               # アクセスログ (JSONL形式)
│   ├── error.log                # 5XXエラー時のPythonトレースバック
│   └── report.log               # CSP等のReporting APIレポート (JSONL形式)
├── src
│   └── nercone_dev
│       ├── __init__.py 
│       ├── __main__.py          # エントリポイント
│       ├── constants.py         # 定数・パス・ホスト名定義
│       ├── logger.py            # ロギング
│       └── website              # HTTPサーバー
│           ├── __init__.py
│           ├── __main__.py
│           ├── databases.py     # MimeTypes/AccessCounter
│           ├── manager.py       # CCManager/PPManager/CSPManager/TimingManager/NetworkManager/OptionManager
│           ├── resolver.py      # ファイル/ページ/短縮URLの解決
│           ├── app.py           # ASGIアプリケーション(FastAPI)/ルーティング定義
│           ├── routes.py        # 定型ルート
│           ├── renderer.py      # ページのレンダリング/サムネイル生成
│           └── middleware.py    # ASGIミドルウェア
├── public/
├── .gitignore
├── README.md
├── CLAUDE.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml
├── update.sh
└── update-contents.sh
```

### `public/`

```
├── .well-known
│   ├── openpgpkey
│   │   ├── hu
│   │   │   ├── mdufcioqzud8czcx79fo1zq1ytp1gggk
│   │   │   └── oonafwamehuud1q4eb4qkd8gfnxyjohn
│   │   ├── nercone.dev
│   │   │   ├── hu
│   │   │   │   ├── mdufcioqzud8czcx79fo1zq1ytp1gggk
│   │   │   │   └── oonafwamehuud1q4eb4qkd8gfnxyjohn
│   │   │   └── policy
│   │   └── policy
│   └── security.txt
├── assets
│   ├── images
│   │   ├── dotcat
│   │   │   ├── 2nd
│   │   │   │   └── ...
│   │   │   ├── error
│   │   │   │   └── ...
│   │   │   ├── forks
│   │   │   │   └── ...
│   │   │   ├── labs
│   │   │   │   └── ...
│   │   │   ├── os
│   │   │   │   └── ...
│   │   │   ├── step
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── dotgirl
│   │   │   └── ...
│   │   ├── thumbnail
│   │   │   ├── template
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── symbol
│   │   │   ├── extended
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── header
│   │   │   └── ...
│   │   ├── wallpaper
│   │   │   └── ...
│   │   ├── 3rd-party
│   │   │   └── ...
│   │   ├── other
│   │   │   └── ...
│   │   └── ...
│   ├── fonts
│   │   └── ...
│   ├── css
│   │   ├── pages
│   │   │   ├── color-palette.css
│   │   │   ├── daily-quote.css
│   │   │   ├── index.css
│   │   │   ├── links.css
│   │   │   ├── qr-code.css
│   │   │   └── sidebar.css
│   │   ├── themes
│   │   │   ├── dark.css
│   │   │   └── light.css
│   │   ├── components
│   │   │   ├── button.css
│   │   │   └── dropdown.css
│   │   ├── main.css
│   │   ├── fonts.css
│   │   ├── colors.css
│   │   ├── cursor.css
│   │   ├── layout.css
│   │   ├── miscellaneous.css
│   │   ├── view-transition.css
│   │   └── loading-overlay.css
│   ├── js
│   │   ├── pages
│   │   │   ├── index.js
│   │   │   └── sidebar.js
│   │   ├── components
│   │   │   └── dropdown.js
│   │   ├── main.js
│   │   ├── cursor.js
│   │   ├── view-transition.js
│   │   ├── loading-overlay.js
│   │   └── class-prefix.js
│   └── pgp
│       ├── nenaicone.asc
│       └── nercone.asc
├── about
│   ├── index.md
│   └── server.md
├── error
│   ├── client.md
│   └── server.html
├── test
│   ├── html.html
│   ├── markdown.md
│   ├── font-size.md
├── base
│   ├── normal.html
│   └── sidebar.html
├── index.html
├── links.html
├── download-banner.md
├── projects.html
├── public-key.html
├── color-palette.md
├── daily-quote.html
├── access-counter.md
├── credit.md
├── options.md
├── qr-code.html
├── vulnerability-reporters.md
├── sitemap.xml
├── quotes.txt
├── robots.txt
├── shorturls.json
└── site.webmanifest
```

## モジュール詳細

### `constants.py` (`src/nercone_dev/constants.py`)
グローバルな定数・パス定義。アプリ起動時に一度だけ評価される。`nercone_dev` パッケージ直下に配置され、`website` サブパッケージと共有される。

- `Directories`: `base`(CWD)、`public`、`logs`、`databases`の`Path`オブジェクト
- `Files`: `mime_types`/`access_counter`の`Path`と、ネストクラス`Files.Logs`(`app`/`access`/`error`/`report`の各ログパス)
- `Repository`: 起動時に`git rev-parse --short HEAD`でコミットハッシュを取得 (`version`)。`git remote get-url origin`でリポジトリURLも取得 (`url`)
- `Hostnames`: `public`(外部公開ドメイン一覧: `nercone.dev`/`nerc1.dev`/`diamondgotcat.net`/`d-g-c.net`) / `local`(`localhost`/`127.0.0.1`) / `all = local + public`
- `Ports`: `http`(`0.0.0.0:80`/`[::]:80`) / `https`(`0.0.0.0:443`/`[::]:443`)
- `TLS`: `certfile`/`keyfile`(既定はLet's Encryptのパス。`WEBSITE_TLS_CERTFILE`/`WEBSITE_TLS_KEYFILE`で上書き可) / `ciphers`(ECDHE-ECDSAスイート列) / `groups`(PQC対応の鍵グループ: X25519MLKEM768等)

### `databases.py` (`src/nercone_dev/website/databases.py`)
永続データの読み書き。

- `MimeTypes`: GitHubの`apache/httpd`リポジトリから`mime.types`を取得し`mimetypes`モジュールに登録する。30日でキャッシュ切れ、起動時 (`__main__`) に1回フェッチし、アプリ初期化 (`app.py`) 時にロードする。
- `AccessCounter`: `databases/access_counter.txt`への排他ロック(`fcntl.LOCK_EX`)を使ったカウンタ。`get()`で読み取り、`increase()`でインクリメント。

### `logger.py` (`src/nercone_dev/logger.py`)
ファイルへの排他ロック書き込みロガー。`nercone_dev` パッケージ直下に配置され、`website` サブパッケージと共有される。

- `format_access(request, response)`: アクセスログ用の辞書を生成する。`id`/`url`/`status`/`method`/`client`/`headers`(リクエスト・レスポンス)/`managers`(cc/pp/csp/timings/network)を含む。スコープは `scope["nercone.dev"]` キーで参照する。
- `Logger.log()`: `logs/app.log`への一般ログ書き込み
- `Logger.log_access()`: `logs/access.log`にJSONL形式で`format_access`の結果を記録し、`app.log`にも1行サマリを書く。
- `Logger.log_error()`: `logs/error.log`へのトレースバック記録。`app.log`にも1行サマリを書く。
- `Logger.log_report(id, body, type)`: `logs/report.log`にCSP等のReporting APIレポートをJSONL形式で記録し、`app.log`にも1行サマリを書く。

### `manager.py` (`src/nercone_dev/website/manager.py`)
リクエストスコープにアタッチされる各種マネージャー。`Middleware.__call__` でインスタンス化され `scope["nercone.dev"]` に格納される。

- `CCManager`: `Cache-Control`ヘッダーを管理。`set()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。`initial`プロパティが`True`の場合はアプリ側で既にヘッダーが設定済みとみなしミドルウェアは上書きしない。
- `PPManager`: `Permissions-Policy`ヘッダーを管理。`set()`/`append()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。
- `CSPManager`: `Content-Security-Policy`ヘッダーを管理。`set()`/`append()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。
- `TimingManager`: `Server-Timing`ヘッダー用の処理時間計測。`start(key, description)`/`stop(key)`でスパンを記録し`header`プロパティで出力。(計測対象: `total`/`receive`/`app`/`app-retry`/`resolve`(ページとショートURL解決の両方で同じキーを使用。2回目以降は`resolve-1`等に自動連番)/`render`/`convert`/`minify`/`compress`/`etag`)
- `NetworkManager`: クライアントのIPアドレス情報を保持。Hypercornがエッジで直接接続を受けるため、`scope["client"]`(実際のTCPピア)から取得する。`trusted`プロパティでプライベートIP帯(RFC 1918/RFC 6890等)か判定。
- `OptionManager`: クエリパラメータとCookieを統合してユーザーオプションを管理。クエリパラメータは`apply()`呼び出し時に自動でCookieに永続化される(`.once`サフィックスを持つキーは永続化されない)。

### `resolver.py` (`src/nercone_dev/website/resolver.py`)
リクエストパスを実際のファイルに解決するロジック。

- `resolve_file(path)`: `public/`配下のファイルを返す。`Path.resolve()` + `is_relative_to()`でディレクトリトラバーサルを防止。存在しない場合は `None`、トラバーサルは `PermissionError`。
- `resolve_page(path, markdown_mode)`: HTMLファイルとMarkdownファイルの候補を優先順位順に探索する。`markdown_mode=True`の場合は`.md`を優先して検索する。
- `resolve_shorturl(path)`: `shorturls.json`を読んで短縮URL(`redirect` または `alias`)を解決する。`alias`はチェーン解決可能で最大10回まで(循環検出あり)。

### `renderer.py` (`src/nercone_dev/website/renderer.py`)
HTTPレスポンスの生成ロジック。

- `CustomHTMLRenderer`: `mistune`のカスタムレンダラー。`block_code`でコードブロックのシンタックスハイライトを無効化、`block_quote`でアラート記法(`[!NOTE]`/`[!WARNING]`等)を`div.block-{type}`に変換する。
- `htmlitdown`: `mistune`インスタンス。プラグイン: `table`/`strikethrough`/`task_lists`/`footnotes`。
- `markitdown`: `MarkItDown()`インスタンス (HTML -> Markdownのリバース変換用)。
- `init_context(context, scope)`: Jinja2テンプレートに渡すコンテキスト辞書を初期化する。`re_sub()`/`this_year`/`this_year_in_heisei`/`daily_quote`を追加する。旧`templates.py`の役割を担う。
- `render_page(page, request, ...)`: 単一ページファイルのレンダリング。YAMLフロントマター解析 → Jinja2レンダリング → `{% extends %}`/`{% block %}`の自動生成の流れ。`markdown_mode`時は`BeautifulSoup`で`<main>`を抽出し`markitdown`でMarkdown変換。
- `default_response(path, request, ...)`: メインのレスポンス生成関数。処理順序:
  1. `resolve_page`でページファイルを探索し`render_page`に渡す
  2. ページ未発見 -> `resolve_file` -> `resolve_shorturl` の順でフォールバック
  3. いずれも不一致で404、ディレクトリトラバーサルで403
  4. ETagの計算と304判定は`middleware.py`の`send()`で行う
- `render_error_page(request, status_code, ...)`: エラーレスポンスの生成。5XXは`error/server.html`をレンダリングなしで返す。4XXは`error/client.md`をコンテキスト付きでレンダリングする。`error_messages`辞書に多数のステータスコード向けメッセージが定義されている。
- `render_thumbnail_svg(path, title, description, template)`: SVGテンプレートの`__PATH__`/`__TITLE__`/`__DESCRIPTION__`を置換してSVG文字列を返す。
- `render_thumbnail_png(path, title, description, template)`: `render_thumbnail_svg`の出力を`resvg_py`で1280×640のPNGに変換する。フォントは`public/assets/fonts/`の NerconeSansJP/NerconeMonoJPを使用。

#### `markdown_mode` の判定ロジック (`renderer.py:68`, `renderer.py:156`)
以下のいずれかに該当する場合は常に`markdown_mode = False`:
- パスが `.html` で終わる
- `Accept` ヘッダーに `text/html` が含まれる

上記に該当せず、さらに以下のいずれかに該当する場合に`markdown_mode = True`となる:
- パスが `.md` で終わる
- `Accept` ヘッダーに `text/markdown` が含まれる
- `User-Agent` ヘッダーに `curl`/`claude-user`/`chatgpt-user`/`google-extended`/`perplexity-user` のいずれかが含まれる (AIクローラー向けに生のMarkdownを返す)

### `middleware.py` (`src/nercone_dev/website/middleware.py`)
ASGI形式のミドルウェア(`Middleware` クラス)。FastAPIの`add_middleware`ではなくStarletteの低レベルASGI形式で実装されており、レスポンスボディを一括取得した後に後処理を行える。

**リクエスト処理フロー:**
1. `scope["type"]`が`http`/`websocket`以外は素通り
2. `scope["nercone.dev"]` に各マネージャー(`id`/`cc`/`pp`/`csp`/`timings`/`network`/`options`) と `templates`(Jinja2Templates)/`accesscounter`(AccessCounter)/`directories`/`files`/`repository`/`hostnames`/`ports`/`tls`/`headers`/`logged`/`compression` を注入
3. `timings.start("total")`
4. ホスト名チェック: `Hostnames.public` 以外のホスト名は403 (trusted networkからのアクセスは除外)
5. URL長チェック: パス + クエリ文字列が1024バイト超の場合は414を返す
6. WebSocket はサブドメインパス変換のみ行い素通り
7. HTTPスキームかつ非trusted networkの場合はHTTPSへ301リダイレクト
8. OPTIONSリクエストは204を返して終了
9. リクエストボディを一括読み取り (`read_body`)
10. サブドメイン処理: `""` / `"www"` 以外のサブドメインはパスに変換 (例: `foo.nercone.dev/bar` -> `/foo/bar`)。サブドメインパスで4XX が返った場合は元のパスでリトライ(`app-retry`)。
11. `send()` でレスポンスを後処理してから送信

**`send()` の後処理:**
- コンテンツ最小化 (`minify`スパン): `text/html` -> `minify_html.minify` / `text/css` -> `rcssmin.cssmin` / `text/javascript`,`application/javascript` -> `rjsmin.jsmin` / `image/svg` -> `scour`(ID短縮/コメント除去)
- レスポンス圧縮 (`compress`スパン): `scope["nercone.dev"]["compression"]`が`True`の場合のみ実行。`Accept-Encoding`に応じて zstd(`zstandard`) / brotli(`brotlicffi`) / gzip / deflate の優先順で圧縮。`Content-Encoding`と`Vary: Accept-Encoding`を付与。フロントマター`compression: false`で個別ページから無効化可能。
- ETag計算 (`etag`スパン): SHA-256でETagを計算し、`If-None-Match`と一致すれば304を返す
- レスポンスヘッダー付与: `Content-Length`/`ETag`/`X-Request-Id`/`X-Frame-Options`/`X-Content-Type-Options`/`Server`/`Link`/`Cache-Control`/`Referrer-Policy`/`Permissions-Policy`/`Content-Security-Policy`/`Reporting-Endpoints`/`Strict-Transport-Security`(HTTPSのみ)/`Cross-Origin-Opener-Policy`(HTMLのみ)/`Cross-Origin-Embedder-Policy`(HTMLのみ)/`Cross-Origin-Resource-Policy`/`Access-Control-*`
- `Server-Timing` を最後に付与 (`stop("total")` の後)
- `Logger.log_access()` でアクセスログを記録

### `app.py` / `routes.py` (`src/nercone_dev/website/`)
`app.py`: FastAPIルーティング定義。`docs_url=None`/`redoc_url=None`/`openapi_url=None` でOpenAPI/Swagger UIは無効。
`routes.py`: `add_report_route(app, path, report_type)` ヘルパーで `/report` および `/report/csp` のReporting APIエンドポイントを動的に追加する。

## エンドポイント一覧

| パス | メソッド | 説明 |
|------|----------|------|
| `/ping` | GET | ヘルスチェック。`pong!`を返す。 |
| `/welcome` | GET | ASCIIアートのウェルカムメッセージ + バージョン情報。 |
| `/echo` | GET | `format_access`の結果をJSONで返す。デバッグ用。trusted networkからのみアクセス可能(それ以外は403)。 |
| `/status` | GET | JSON形式のステータス。`status`/`version`(サーバーコミットハッシュ)/`counter`(アクセス数)を含む。 |
| `/assets/images/thumbnail/template/{template}` | GET | サムネイルPNG生成。クエリ: `path`/`title`/`description`。 |
| `/assets/css/merge` | GET | CSSファイルの結合。クエリ`path`にカンマ区切りでファイル名(拡張子なし)を指定。`@charset`/`@import`を整理してボディを結合する。 |
| `/assets/js/merge` | GET | JSファイルの結合。クエリ`path`にカンマ区切りでファイル名(拡張子なし)を指定。 |
| `/error/{status_code}` | GET | エラーページのプレビュー。`server`またはHTTPステータスコードを指定。 |
| `/report` | POST | Reporting APIレポートの受信 (DEFAULT)。`application/reports+json`または`application/csp-report`形式、65536バイト上限。`logs/report.log`に記録。 |
| `/report/csp` | POST | CSPレポートの受信。同上。 |
| `/{path:path}` | GET/POST/HEAD | メインルート。`resolve_page` -> `resolve_file` -> `resolve_shorturl` の順でレスポンスを決定。 |

## 設定と起動

### 環境変数
- `WEBSITE_TLS_CERTFILE`/`WEBSITE_TLS_KEYFILE`: TLS証明書・秘密鍵のパス(既定はLet's Encryptのパス)。未設定の場合は`Ports.http`(`0.0.0.0:80`/`[::]:80`)でTCPリッスン。

### 起動コマンド
```sh
# 開発時 (直接実行)
uv run nercone-dev

# 開発/テスト時 (Docker Compose)
docker compose up -d -f docker-compose.dev.yml

# 本番 (Docker Compose)
docker compose up -d
```

### Docker構成
- マルチステージビルド構成
  1. `openssl-builder` (`cgr.dev/chainguard/wolfi-base`): OpenSSLを最新リリースからソースビルド (kTLS有効、ktlsはLinux 4.13以降)
  2. `builder` (`cgr.dev/chainguard/wolfi-base`): uvで依存関係をインストールし`.venv`を構築
  3. 最終イメージ (`cgr.dev/chainguard/wolfi-base`): `.venv`とソースのみをコピーしたランタイムイメージ
- `docker-compose.yml`で`network_mode: host`を使用(`:80`/`:443` TCP・`:443` UDPを直接使用、特権ポートbindのためroot実行)
- `/etc/letsencrypt`を読み取り専用でマウント (TLS証明書)
- `logs/`/`databases/`はバインドマウントで永続化
- `public/`は読み取り専用でマウント (`:ro`)
- `.git/`も読み取り専用でマウント (バージョン情報取得用)

## コンテンツレンダリング仕様

### フロントマター
HTMLファイルとMarkdownファイルの先頭に `---` で囲まれたYAML形式のフロントマターを記述できる。

```yaml
---
base: normal       # 継承するベーステンプレート (デフォルト: normal, /base/normal.html)
title: ページタイトル   # テンプレートのtitleブロックを上書き
description: 説明文    # その他のブロックも任意に指定可能
---
```

フロントマターが設定されている場合、`{% extends "..." %}` と各 `{% block %}` が自動生成され、Jinja2でレンダリングされる。

### テンプレート変数
Jinja2テンプレート内で利用可能なグローバル変数/関数:

- `request`: Starletteの`Request`オブジェクト
- `this_year()`: 日本時間の現在年
- `this_year_in_heisei()`: 平成換算の現在年 (year - 1988)
- `daily_quote`: `quotes.txt`から日付をシードにして1日1エントリを選択した文字列 (UTCの日付でシード)
- `re_sub(s, pattern, repl)`: 正規表現置換 (テンプレート内では `s | re_sub(pattern, repl)` の形で使用)
- その他`scope["nercone.dev"]`の全キー (`repository`/`hostnames`/`accesscounter`等) もコンテキスト経由で参照可能

### 短縮URL (`shorturls.json`)

```json
{
  "short-key": {"type": "redirect", "content": "https://..."},
  "alias-key": {"type": "alias", "content": "other-short-key"}
}
```

- `redirect` — 307リダイレクト
- `alias` — 別のキーにフォールバック (最大10チェーン、循環検出あり)

## 依存関係

| パッケージ | 用途 |
|-----------|------|
| `fastapi` | WebフレームワークとルーティングAPI |
| `hypercorn[h3,uvloop]` | ASGIサーバー兼TLS終端エッジ (h3=aioquicによるHTTP/3、uvloop=高速イベントループ。WebSocketはwsprotoで内蔵) |
| `aioquic` | HTTP/3のQUIC実装 (nercone-forksのPQCサポートブランチを使用) |
| `jinja2` | HTMLテンプレートエンジン |
| `mistune` | Markdown -> HTML変換 |
| `markitdown` | HTML -> Markdown変換 (CLIツール/AIクローラー向けレスポンス用) |
| `beautifulsoup4` | HTML解析 (markdown_modeで`<main>`要素抽出) |
| `resvg-py` | SVG -> PNG変換 (サムネイル生成) |
| `scour` | SVGの最適化/最小化 |
| `rjsmin` | JavaScriptの最小化 |
| `rcssmin` | CSSの最小化 |
| `minify-html` | HTMLの最小化 (JS/CSSインラインも対象) |
| `zstandard` | レスポンス圧縮 (zstd) |
| `brotlicffi` | レスポンス圧縮 (brotli) |
| `httpx[http2]` | HTTP/2クライアント (mime.typesのフェッチ) |
| `websockets` | WebSocketサポート |
| `fourword` | [FourWord ID](https://github.com/nercone-dev/fourword/)の生成 |
| `pyyaml` | フロントマターのYAML解析 |

## Claudeによるコミット
コードやコンテンツに変更を加える場合、次を遵守してください。

- 可能な限り既存のコードのスタイルや構造を維持し、その上でシンプルな方法を用いて機能の実装や問題の解決を行い、可読性の高いコードで実装してください。
- 各機能/モジュールは他の機能/モジュールや共通部分に、その機能/モジュール専用のコードを含めないように努力してください。追加する以外の方法が全く存在しない場合、追加されるコードを最低限に抑えてください。
- 安全性や信頼性に少しでも影響がある場合、可能な限り慎重に実装方法を検討してください。
- 人間が変更内容を誤解なく完全な状態で理解できる必要があります。作業中に中程度の頻度で詳細な作業ログを目立つ形で提供してください。

人間によるレビューで承認され、人間によりコミットの作成が要求された場合、次を遵守した上でコミットを作成することができます。

- 実際にコミットを作成する前に、作成する際に使用するコミットメッセージや、コミットに含める(つまり、`git add`でステージングする)変更を詳細にまとめ、人間に伝え、承認され次第コミットを作成してください。
- コミットメッセージは日本語で書いてください。
- コミットメッセージの終盤に英語への翻訳も記載してください。
- コミットメッセージの1行目のテキストは、コミットの内容や2行目以降の内容を知らない場合でも簡単にコミットの内容を理解できるものにしてください。
- コミットメッセージの2/3行目以降で、より詳細な変更内容をまとめてください。
- コミットメッセージの1行目に`Claude: `プレフィックスを付けてください。
- `Assisted-by: AGENT_NAME:MODEL_VERSION [TOOL 0] [TOOL 1]`の形式のトレーラーをコミットに含ませてください。
    - `AGENT_NAME`には`Claude`/`ChatGPT`/`Gemini`のような名称を使用してください。
    - `MODEL_VERSION`には`claude-sonnet-4.6`のようなテキストを使用してください。
    - `[TOOL 0] [TOOL 1]`の部分は、コードを分析するのに使用したツールの名称を空白区切りで記載してください。
        - gitやuv、clangなどの日常的に使用される基本的なツールについては、記載する必要はありません。

## 補足
- `/status`エンドポイントのレスポンスには起動時に`git rev-parse --short HEAD`で取得したサーバーのコミットハッシュを含むため、更新後に変更が正しく反映されているか確認できます。
- アクセスログは`logs/access.log`にJSONL形式で記録されます。ログエントリには `id`/`url`/`status`/`method`/`client`/`headers`/`managers`(cc/pp/csp/timings/network)が含まれます。
- 5XXエラーが発生した場合は`logs/error.log`にPythonのトレースバックが記録されます。リクエストIDでアクセスログと照合できます。
- リクエストIDは[FourWord ID](https://github.com/nercone-dev/fourword/)のText形式が採用されており、テキスト形式に変換された後`X-Request-Id`レスポンスヘッダーとして返されます。幅が少し狭いターミナルでも折り返しが発生しないよう、`app.log`ファイルではCompact Text形式が採用されています。 
- `Server-Timing`ヘッダーで各処理段階の所要時間を確認できます。
- アクセスカウンタなどの一部の例外を除き、外部からのアクセスに対して`public/`ディレクトリ外のファイルのコンテンツに関する情報、またはそれを予測できるような情報は、リクエストに少しも含めてはなりません。
  これはセキュリティ上最も重要と言えます。そのため、このルールに従わない手法での機能の実装方法や問題の解決策は考えるべきではありません。

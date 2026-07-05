# CLAUDE.md
このファイルは、Claude Codeがこのリポジトリ内のコードを扱う際に知っておくべき情報を提供するものです。

## 概要
ここは[nercone.dev](https://nercone.dev/)のソースコードを管理するリポジトリです。

`nercone_website` パッケージの下にHTTPサーバーの実装が配置されています。

- `nercone_website`: Python 3.12のFastAPI + Uvicornの上で動くASGIアプリケーション

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
│   ├── main.log                 # 一般ログ (アクセス/エラー/レポートの1行サマリ)
│   ├── access.log               # アクセスログ (JSONL形式)
│   ├── error.log                # 5XXエラー時のPythonトレースバック
│   ├── reports.log              # CSP等のReporting APIレポート (JSONL形式)
│   └── warnings.log             # 警告レベルのイベント (レポート受信時など)
├── src
│   └── nercone_website
│       ├── __init__.py
│       ├── __main__.py          # エントリポイント (uvicorn起動)
│       ├── constants.py         # 定数・パス・ホスト名定義
│       ├── logger.py            # ロギング (nercone-modernのLoggingを使用)
│       ├── databases.py         # MimeTypes/AccessCounter
│       ├── models.py            # CCManager/PPManager/CSPManager/TimingManager/NetworkManager/OptionManager
│       ├── resolver.py          # ファイル/ページ/リダイレクトの解決
│       ├── app.py               # ASGIアプリケーション(FastAPI)/ルーティング定義
│       ├── routes.py            # 定型ルート
│       ├── renderer.py          # ページのレンダリング/サムネイル生成
│       └── middleware.py        # ASGIミドルウェア
├── public/
├── .gitignore
├── README.md
├── TODO.md
├── CLAUDE.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yml           # 本番用
├── docker-compose.dev.yml       # 開発/テスト用
└── update.sh                    # git pull -> Python/Wolfiパッケージのバージョン確認 -> Dockerビルド・再起動
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
│   │   │   └── ...
│   │   ├── dotgirl
│   │   │   └── ...
│   │   ├── thumbnail
│   │   │   ├── template
│   │   │   │   └── ...
│   │   │   └── ...
│   │   ├── symbol
│   │   │   └── ...
│   │   ├── header
│   │   │   └── ...
│   │   ├── wallpaper
│   │   │   └── ...
│   │   ├── other
│   │   │   └── ...
│   │   └── ...
│   ├── fonts
│   │   └── ...                  # Nercone Sans (JP/SC/TC/KR) / Nercone Mono JP 各ウェイト
│   ├── sounds
│   │   ├── Mirai.band
│   │   ├── Zerc.band
│   │   └── Zercone.band
│   ├── css
│   │   ├── pages
│   │   │   ├── color-palette.css
│   │   │   ├── daily-quote.css
│   │   │   ├── index.css
│   │   │   ├── infra.css
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
│   │   ├── noscript.css
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
├── docs
│   ├── index.md
│   └── test
│       └── ...
├── error
│   ├── client.md
│   └── server.html
├── test
│   ├── html.html
│   ├── markdown.md
│   ├── font-size.md
│   └── sidebar.html
├── base
│   ├── normal.html
│   └── sidebar.html
├── favicon.ico
├── index.html
├── links.html
├── download-banner.md
├── projects.html
├── public-key.html
├── color-palette.md
├── daily-quote.html
├── access-counter.md
├── credit.md
├── infra.md
├── options.md
├── qr-code.html
├── vulnerability-reporters.md
├── sitemap.xml
├── quotes.txt
├── robots.txt
├── redirects.json
└── site.webmanifest
```

## モジュール詳細

### `constants.py` (`src/nercone_website/constants.py`)
グローバルな定数・パス定義。アプリ起動時に一度だけ評価される。

- `reserved_cookie_keys`: `http.cookies.Morsel._reserved` から生成した予約済みCookieキーの集合 (`OptionManager.apply`で使用)
- `Startup`: `id`(`WEBSITE_ID`環境変数、未設定なら起動時に生成される`FourWord`) / `dev`(`WEBSITE_DEV=1`で有効化)
- `Directories`: `base`(CWD)、`public`、`logs`、`databases`の`Path`オブジェクト
- `Files`: `mime_types`/`access_counter`の`Path`と、ネストクラス`Files.Logs`(`main`/`error`/`access`/`reports`/`warnings`の各ログパス)
- `Repository`: 起動時に`git rev-parse --short HEAD`でコミットハッシュを取得 (`version`)。`git remote get-url origin`でリポジトリURLも取得 (`url`)
- `Hostnames`: `public`(外部公開ドメイン一覧: `nercone.dev`/`nerc1.dev`/`diamondgotcat.net`/`d-g-c.net`) / `local`(`localhost`/`127.0.0.1`) / `all = local + public`
- `Ports`: `tcp`(`WEBSITE_TCP`環境変数、既定`8080`) / `uds`(`WEBSITE_UDS`環境変数、Unixドメインソケットのパス。未設定ならUDSリッスンなし)

TLS終端やHTTP/3対応は行っておらず、リバースプロキシ側で処理される前提の構成になっている。

### `databases.py` (`src/nercone_website/databases.py`)
永続データの読み書き。

- `MimeTypes`: GitHubの`apache/httpd`リポジトリから`mime.types`を取得し`mimetypes`モジュールに登録する。30日でキャッシュ切れ、起動時 (`__main__`) に1回フェッチし、アプリ初期化 (`app.py`) 時にロードする。
- `AccessCounter`: `databases/access_counter.txt`への排他ロック(`fcntl.LOCK_EX`)を使ったカウンタ。ファイルが存在しない場合は`0`で初期化する。`get()`で読み取り、`increase()`でインクリメント。

### `logger.py` (`src/nercone_website/logger.py`)
`nercone-modern`パッケージの`Logging`クラスを利用したロギング。`logs/main.log`/`error.log`/`access.log`/`reports.log`/`warnings.log`にそれぞれ対応するロガーインスタンス(`logger_main`/`logger_error`/`logger_access`/`logger_reports`/`logger_warnings`)を持つ。

- `format_access(request, response)`: アクセスログ用の辞書を生成する。`id`/`url`/`status`/`method`/`client`/`headers`(リクエスト・レスポンス)/`managers`(cc/pp/csp/timings/network)を含む。スコープは `scope["website"]` キーで参照する。
- `log_access(request, response, status_code)`: `main.log`に1行サマリ(`{id} STATUS {code} FROM {host}:{port} TO {url}`)を書き、`access.log`に`format_access`の結果をJSONL形式で記録する。
- `log_report(request, body, report_type)`: `warnings.log`に1行サマリを書き、`reports.log`に`format_access`の結果と`report`キーをマージしてJSONL形式で記録する。
- `log_error(id, traceback)`: `error.log`へのトレースバック記録。

### `models.py` (`src/nercone_website/models.py`)
リクエストスコープにアタッチされる各種マネージャー。`Middleware.__call__` でインスタンス化され `scope["website"]` に格納される。

- `CCManager`: `Cache-Control`ヘッダーを管理。`set()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。`initial`プロパティが`True`の場合はアプリ側で既にヘッダーが設定済みとみなしミドルウェアは上書きしない。
- `PPManager`: `Permissions-Policy`ヘッダーを管理。既定で`camera`/`microphone`/`geolocation`/`payment`/`usb`/`accelerometer`/`gyroscope`/`magnetometer`/`display-capture`を全て拒否。`set()`/`append()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。
- `CSPManager`: `Content-Security-Policy`ヘッダーを管理。既定で`default-src 'none'`をベースに`assets.nercone.dev`等を許可するディレクティブを持つ。`set()`/`append()`/`remove()`で操作し`header`プロパティでヘッダー文字列化。
- `TimingManager`: `Server-Timing`ヘッダー用の処理時間計測。`start(key, description)`/`stop(key)`でスパンを記録し`header`プロパティで出力。(計測対象: `total`/`receive`/`app`/`app-retry`/`resolve`(ページとリダイレクト解決の両方で同じキーを使用。2回目以降は`resolve-1`等に自動連番)/`render`/`convert`/`minify`/`compress`/`etag`)
- `NetworkManager`: クライアントのIPアドレス情報を保持。Uvicornが直接接続を受けるため、`scope["client"]`から取得する。`trusted`プロパティでプライベートIP帯(RFC 1918/RFC 6890等、CGNAT`100.64.0.0/10`含む)か判定。
- `OptionManager`: クエリパラメータとCookieを統合してユーザーオプションを管理。クエリパラメータは`apply()`呼び出し時に自動でCookieに永続化される(`.once`サフィックスを持つキーは永続化されない、`reserved_cookie_keys`に含まれるキーは無視される)。

### `resolver.py` (`src/nercone_website/resolver.py`)
リクエストパスを実際のファイルに解決するロジック。

- `resolve_file(path)`: `public/`配下のファイルを返す。`Path.resolve()` + `is_relative_to()`でディレクトリトラバーサルを防止。存在しない場合は `None`、トラバーサルは `PermissionError`。
- `resolve_page(path, markdown_mode, timings)`: HTMLファイルとMarkdownファイルの候補を優先順位順に探索する。`markdown_mode=True`の場合は`.md`を優先して検索する。
- `resolve_redirects(path, timings)`: `redirects.json`を読んで`redirect`または`alias`を解決する。`alias`はチェーン解決可能で最大10回まで(循環検出あり)。

### `renderer.py` (`src/nercone_website/renderer.py`)
HTTPレスポンスの生成ロジック。

- `CustomHTMLRenderer`: `mistune`のカスタムレンダラー。`block_code`でコードブロックのシンタックスハイライトを無効化、`block_quote`でアラート記法(`[!NOTE]`/`[!WARNING]`等)を`div.block-{type}`に変換する。
- `htmlitdown`: `mistune`インスタンス。プラグイン: `table`/`strikethrough`/`task_lists`/`footnotes`。
- `markitdown`: `MarkItDown()`インスタンス (HTML -> Markdownのリバース変換用)。
- `init_context(context, scope)`: Jinja2テンプレートに渡すコンテキスト辞書を初期化する。`scope["website"]`の全キーをマージした上で`re_sub()`/`this_year`/`this_year_in_heisei`/`daily_quote`を追加する。
- `render_page(page, path, request, ...)`: 単一ページファイルのレンダリング。YAMLフロントマター解析 → Jinja2レンダリング → `{% extends %}`/`{% block %}`の自動生成の流れ。`markdown_mode`時は`BeautifulSoup`で`<main>`を抽出し`markitdown`でMarkdown変換。フロントマターの`compression`キーで`scope["website"]["compression"]`を上書きできる。
- `default_response(path, request, ...)`: メインのレスポンス生成関数。処理順序:
  1. `resolve_redirects`でリダイレクト解決 (307等)
  2. `resolve_page`でページファイルを探索し`render_page`に渡す
  3. `resolve_file`でファイル配信 (`FileResponse`)
  4. いずれも不一致で404、ディレクトリトラバーサルで403
  5. ETagの計算と304判定は`middleware.py`の`send()`で行う
- `render_error_page(request, status_code, ...)`: エラーレスポンスの生成。5XXは`error/server.html`をレンダリングなしで返す(CSPに`'unsafe-inline'`とGoogle Fontsを追加)。4XXは`error/client.md`をコンテキスト付きでレンダリングする。`error_messages`辞書に多数のステータスコード向けメッセージが定義されている。
- `render_thumbnail_svg(path, title, description, template)`: SVGテンプレートの`__PATH__`/`__TITLE__`/`__DESCRIPTION__`を置換してSVG文字列を返す。
- `render_thumbnail_png(path, title, description, template)`: `render_thumbnail_svg`の出力を`resvg_py`で1280×640のPNGに変換する。フォントは`public/assets/fonts/`のNerconeSans(JP/SC/TC/KR)/NerconeMonoJP各ウェイトを使用。

#### `markdown_mode` の判定ロジック (`renderer.py`の`render_page`/`default_response`)
以下のいずれかに該当する場合に`markdown_mode = True`となる:
- パスが `.md` で終わる
- `Accept` ヘッダーに `text/markdown` が含まれる
- `User-Agent` ヘッダーが `curl` で始まる

### `middleware.py` (`src/nercone_website/middleware.py`)
ASGI形式のミドルウェア(`Middleware` クラス)。FastAPIの`add_middleware`ではなくStarletteの低レベルASGI形式で実装されており、レスポンスボディを一括取得した後に後処理を行える。

**リクエスト処理フロー:**
1. `scope["type"]`が`http`/`websocket`以外は素通り
2. `scope["website"]` に各マネージャー(`id`/`cc`/`pp`/`csp`/`timings`/`network`/`options`) と `templates`(Jinja2Templates)/`accesscounter`(AccessCounter)/`directories`/`files`/`repository`/`hostnames`/`headers`/`logged`/`compression` を注入
3. `timings.start("total")`
4. 開発モード(`Startup.dev`)ではCSPの`script-src`/`style-src`/`font-src`/`img-src`に`localhost:{Ports.tcp}`を追加
5. ホスト名チェック: `Hostnames.public` に一致しないホスト名は403 (trusted networkからのアクセスは除外)
6. URL長チェック: パス + クエリ文字列が256バイト超の場合は414を返す
7. WebSocket はサブドメインパス変換のみ行い素通り
8. OPTIONSリクエストは204を返して終了
9. リクエストボディを一括読み取り (`read_body`)
10. サブドメイン処理: `""` / `"www"` 以外のサブドメインはパスに変換 (例: `foo.nercone.dev/bar` -> `/foo/bar`)。サブドメインパスで4XX が返った場合は元のパスでリトライ(`app-retry`)。
11. `send()` でレスポンスを後処理してから送信

HTTP→HTTPSのリダイレクトやTLS証明書の扱いはこのミドルウェアには存在せず、リバースプロキシ側の責務となっている。

**`send()` の後処理:**
- 開発モード(`Startup.dev`)では`text/html`/`text/css`/`text/javascript`/`application/javascript`/`text/svg`のボディ中の`https://assets.nercone.dev/`を`http://localhost:{Ports.tcp}/assets/`に置換
- コンテンツ最小化 (`minify`スパン): `text/html` -> `minify_html`(`minify_js`/`minify_css`有効, コメント保持) / `text/css` -> `rcssmin.cssmin` / `text/javascript`,`application/javascript` -> `rjsmin.jsmin` / `text/svg` -> `scour`(ID短縮/コメント除去)。各変換関数は`functools.lru_cache`でキャッシュされる。
- レスポンス圧縮 (`compress`スパン): `scope["website"]["compression"]`が`True`かつボディが空でない場合のみ実行。`Accept-Encoding`に応じて zstd(`zstandard`, level=3) / brotli(`brotlicffi`, quality=4) / gzip(level=6) / deflate(level=6) の優先順で圧縮しキャッシュ。`Content-Encoding`と`Vary: Accept-Encoding`を付与。フロントマター`compression: false`で個別ページから無効化可能。
- ETag計算 (`etag`スパン): `xxhash.xxh3_128`でETagを計算(`lru_cache`でキャッシュ)し、`If-None-Match`と一致すれば304を返す
- レスポンスヘッダー付与: `Content-Length`/`ETag`/`Server`/`X-Powered-By`/`X-Request-Id`/`Link`(sitemap/robots)/`X-Content-Type-Options`/`Reporting-Endpoints`/`Cache-Control`(font=604800s、css/js=43200s、その他はno-cache、`CCManager`側で設定済みなら優先)/`Referrer-Policy`/`Permissions-Policy`/`Content-Security-Policy`/`X-Frame-Options`/`Cross-Origin-Opener-Policy`(HTMLのみ)/`Cross-Origin-Resource-Policy`/`Access-Control-*`(静的アセット系は`*`許可、それ以外は`Hostnames.all`に一致するOriginのみ許可)
- `Server-Timing` を最後に付与 (`stop("total")` の後)
- `log_access()` でアクセスログを記録 (`scope["website"]["logged"]`で二重記録を防止)

### `app.py` / `routes.py` (`src/nercone_website/`)
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
| `/report` | POST | Reporting APIレポートの受信 (DEFAULT)。`application/reports+json`または`application/csp-report`形式、65536バイト上限。`logs/reports.log`に記録。 |
| `/report/csp` | POST | CSPレポートの受信。同上。 |
| `/{path:path}` | GET/POST/HEAD | メインルート。`resolve_redirects` -> `resolve_page` -> `resolve_file` の順でレスポンスを決定。 |

## 設定と起動

### 環境変数
- `WEBSITE_TCP`: TCPリッスンポート (既定`8080`)。
- `WEBSITE_UDS`: Unixドメインソケットのパス (未設定ならUDSリッスンなし)。
- `WEBSITE_DEV`: `1`を指定すると開発モード(`nercone-website dev`起動時に自動設定)。CSPへのlocalhost許可やアセットURLのローカル書き換えが有効化される。
- `WEBSITE_ID`: プロセスの`Startup.id`(FourWord)を固定したい場合に指定。

### 起動コマンド
```sh
# 開発時 (直接実行、ホットリロード有効)
uv run nercone-website dev

# 開発/テスト時 (Docker Compose)
docker compose -f docker-compose.dev.yml up -d

# 本番 (Docker Compose)
docker compose up -d
```

本番起動時は`__main__.py`がTCPソケット(常に)とUDSソケット(`WEBSITE_UDS`設定時のみ)を自前でbindし、`uvicorn.supervisors.Multiprocess`で4ワーカーを起動する(`uvicorn.Config(workers=4)`)。

### Docker構成
- マルチステージビルド構成
  1. `python-builder` (`cgr.dev/chainguard/wolfi-base`): 指定バージョンのCPythonをソースからビルド (`--enable-optimizations --with-lto`)
  2. `builder` (`cgr.dev/chainguard/wolfi-base`): uvで依存関係をインストールし`.venv`を構築
  3. 最終イメージ (`cgr.dev/chainguard/wolfi-base`): ビルド済みPython・`.venv`・ソースのみをコピーしたランタイムイメージ
- コンテナは`8080:8080`のみを公開し、特権ポートのbindやTLS終端は行わない (リバースプロキシ側の責務)
- `docker-compose.yml`(本番)は`/run/website`(UDSソケット用)をバインドマウントし、`WEBSITE_TCP`/`WEBSITE_UDS`環境変数を設定
- `docker-compose.dev.yml`(開発)は`WEBSITE_DEV=1`を設定し、UDSは使用しない
- `logs/`/`databases/`はバインドマウントで永続化、`public/`は読み取り専用マウント(`:ro`)、`.git/`も読み取り専用マウント(バージョン情報取得用)
- `update.sh`: `git pull` -> CPythonの最新3.13系バージョンとWolfiパッケージ(Dockerfile中の`apk add`対象)のバージョンハッシュを取得 -> `docker compose build --build-arg ...` -> `docker compose up -d`

## コンテンツレンダリング仕様

### フロントマター
HTMLファイルとMarkdownファイルの先頭に `---` で囲まれたYAML形式のフロントマターを記述できる。

```yaml
---
base: normal       # 継承するベーステンプレート (デフォルト: normal, /base/normal.html)
title: ページタイトル   # テンプレートのtitleブロックを上書き
description: 説明文    # その他のブロックも任意に指定可能
compression: "false"  # レスポンス圧縮を個別ページから無効化 (文字列の"true"/"false")
---
```

フロントマターが設定されている場合、`{% extends "..." %}` と各 `{% block %}` が自動生成され、Jinja2でレンダリングされる。

### テンプレート変数
Jinja2テンプレート内で利用可能なグローバル変数/関数:

- `request`: Starletteの`Request`オブジェクト
- `this_year`: 日本時間の現在年
- `this_year_in_heisei`: 平成換算の現在年 (year - 1988)
- `daily_quote`: `quotes.txt`から日付をシードにして1日1エントリを選択した文字列 (UTCの日付でシード)
- `re_sub(s, pattern, repl)`: 正規表現置換 (テンプレート内では `s | re_sub(pattern, repl)` の形で使用)
- その他`scope["website"]`の全キー (`repository`/`hostnames`/`accesscounter`等) もコンテキスト経由で参照可能

### リダイレクト (`redirects.json`)

```json
{
  "short-key": {"type": "redirect", "content": "https://..."},
  "alias-key": {"type": "alias", "content": "other-short-key"}
}
```

- `redirect` — 307リダイレクト (または呼び出し元が指定した3XXステータス)
- `alias` — 別のキーにフォールバック (最大10チェーン、循環検出あり)

## 依存関係

| パッケージ | 用途 |
|-----------|------|
| `fastapi` | WebフレームワークとルーティングAPI |
| `uvicorn[standard]` | ASGIサーバー (TLS終端・HTTP/3対応なし、リバースプロキシ配下での運用が前提) |
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
| `xxhash` | ETag計算 (xxHash3-128) |
| `httpx[http2]` | HTTP/2クライアント (mime.typesのフェッチ) |
| `websockets` | WebSocketサポート |
| `nercone-modern` | ファイルロギング (`Logging`クラス) |
| `fourword` | [FourWord ID](https://github.com/nercone-dev/fourword/)の生成 |
| `pyyaml` | フロントマターのYAML解析 |
| `tzdata` | タイムゾーンデータ (`this_year`等の日本時間計算用) |

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
- リクエストIDは[FourWord ID](https://github.com/nercone-dev/fourword/)のText形式が採用されており、`X-Request-Id`レスポンスヘッダーとして返されます。`logs/main.log`のサマリ行にもこのID(Text形式)が使用されています。
- `Server-Timing`ヘッダーで各処理段階の所要時間を確認できます。
- アクセスカウンタなどの一部の例外を除き、外部からのアクセスに対して`public/`ディレクトリ外のファイルのコンテンツに関する情報、またはそれを予測できるような情報は、リクエストに少しも含めてはなりません。
  これはセキュリティ上最も重要と言えます。そのため、このルールに従わない手法での機能の実装方法や問題の解決策は考えるべきではありません。

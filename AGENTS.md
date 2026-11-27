# AGENTS.md

[nercone.dev](https://nercone.dev/) のWebサイトのソースコードです。FastAPI + Jinja2 で動作し、VPS上のDockerで運用しています。

このファイルは、ユーザー共通のルール(`~/.claude/CLAUDE.md` など)に加えて、このリポジトリ固有の事項をまとめたものです。`CLAUDE.md` は、このファイルへのシンボリックリンクです。

## 最重要ルール: `/private/` は絶対に公開しない

`/private/`(リポジトリ直下の `private/`)には、ログ(`logs/`)やデータベース(`databases/`)など、非公開のデータが入ります。**その内容は、いかなる方法でも絶対に公開されない設計にしてください。** 例外はありません。

- HTTPで配信される対象は `public/` 以下だけです。`private/` を配信ルート、静的ファイルの探索対象、テンプレートの探索対象にしないでください。
- `private/` の内容(ファイルの中身、ファイル名、一覧、サイズ、更新日時、統計値など、そこから導ける情報を含む)を、レスポンス、エラーメッセージ、ステータスページ、API、ログ出力、サイトマップ、`llms.txt` などに含めないでください。
- `private/` を `public/` 内へコピー、シンボリックリンク、バンドル、キャッシュ、出力しないでください。逆に、公開してはいけないものは `public/` に置かないでください。
- パスを受け取る処理は、解決後(`resolve()`)のパスが `public/` 配下であることを必ず確認してください。現在は `src/website/resolver.py` の `ensure_public_path()` がこれを担っています。`..`、シンボリックリンク、URLエンコード、大文字小文字、重複スラッシュによる迂回を想定してください。この検証を弱めたり、迂回する経路を作ったりしないでください。
- 新しい配信経路(ルート、静的ファイル配信、ダウンロード、プロキシなど)を追加するときは、その経路から `private/` に到達できないことを確認し、可能ならテストで検証してください。
- `private/` は `.gitignore` に含まれています。この設定を外さないでください。Gitにコミットしたり、`git add -f` したりしないでください。
- Dockerイメージに `private/` を含めないでください。`Dockerfile` は `src` だけを `COPY` します。この方針を変える場合(`COPY . .` の追加など)は、先に `.dockerignore` で `private/` を除外してください。`private/` はコンテナへ実行時のボリュームとしてだけ渡します。
- ログ・データベースの書き込みなど、アプリ内部からの利用は構いません。ただし、読み出した内容を外部へ出す機能は作らないでください。
- AIエージェントとして `private/` を読む必要がある場合も、内容を回答、コミット、ドキュメント、外部サービスへの送信に含めないでください。

判断に迷う場合は、公開しない側に倒してください。

## ディレクトリ構造

```
.
├── AGENTS.md / CLAUDE.md      このファイル(CLAUDE.mdはシンボリックリンク)
├── README.md
├── pyproject.toml / uv.lock   Pythonパッケージ(uv_build)。パッケージ名 nercone-website
├── Dockerfile                 マルチステージビルド(builder → distroless)
├── docker-compose.yml         本番用
├── docker-compose.dev.yml     開発用(-f で重ねて使う)
├── .env / .env.example        Conetの鍵など(.envはGit管理外)
├── conet/services             Conetのサービス定義(443 → 127.0.0.1:8000)
├── nginx/nginx.conf           リバースプロキシの設定
├── src/website/               アプリケーション本体
│   ├── __main__.py            エントリポイント(ソケットを作成して uvicorn を起動)
│   ├── app.py                 FastAPIアプリ
│   ├── middleware.py          ミドルウェア
│   ├── renderer.py            Jinja2/Markdownのレンダリング
│   ├── resolver.py            URLからファイル・ページ・リダイレクトを解決(public配下に限定)
│   ├── constants.py           ディレクトリ・ホスト名・ポートなどの定数
│   ├── logger.py              ログ出力
│   └── helpers/               MIME、システム情報(status用)、バンドルなどの補助
├── public/                    公開してよいものだけを置く(HTTPで配信される範囲)
│   ├── static/                静的ファイル(assets/、robots.txt、redirects.json、sitemap.xml など)
│   ├── templates/             ページ(.html / .md)。base/ にレイアウト、about/ design/ status/ error/ などのページ
│   └── data/                  実行時に生成されるデータ(Git管理外)
├── private/                   非公開データ(Git管理外・絶対に公開しない): logs/, databases/
├── data/                      実行時データ(Git管理外): data/certs/ に証明書
├── tools/                     start.sh, update.sh, png2jxl.sh
│   └── sounds/                サウンド(Zerc / Zercone / Mirai)の作曲・レンダリング(.docs/sounds.md)
├── .docs/                     開発者向けドキュメント
└── .claude/launch.json        開発サーバー(website-dev)の起動定義
```

`public/templates/` では、URLパスから `{name}.html` → `{name}/index.html` → `{name}/README.html` → `.md` の順(Markdown優先のリクエスト時は逆)にページを探します(`resolver.py` の `page_candidates()`)。

## 実行環境とサーバー構成

### アプリケーション

- Python 3.12〜3.14 に対応します(`pyproject.toml`)。本番イメージは `tools/start.sh` が取得した最新の CPython 3.13.x を使います。
- 起動コマンドは `nercone-website`(`website.__main__:main`)です。
    - 本番: uvicorn、4ワーカー(`Multiprocess`)。
    - 開発(`WEBSITE_DEV=1`): リロード有効。
- 待ち受けは、TCP(`WEBSITE_TCP_HOST` / `WEBSITE_TCP_PORT`、既定 `0.0.0.0:8080`)と、`WEBSITE_UDS` を指定した場合はUNIXドメインソケットの両方です。
- `/ping` はヘルスチェック用のエンドポイントです。
- ベースディレクトリは `Path.cwd()` です。`public/` と `private/` は作業ディレクトリ(コンテナでは `/srv/website`)からの相対位置で決まります。

### 本番(`docker-compose.yml`)

4つのコンテナが、`conet` のネットワーク名前空間を共有します(`network_mode: service:conet`)。

| サービス | イメージ | 役割 |
| --- | --- | --- |
| `conet` | `ghcr.io/nercone-infra/conet-agent` | Conetのエージェント。`conet/services` に従い、443番で受けた通信を `127.0.0.1:8000` へ渡す。`NET_ADMIN` が必要。 |
| `cert` | `ghcr.io/nercone-infra/cert-agent` | `data/certs/` の証明書を管理する。 |
| `nginx` | `nginx:stable-trixie` | `127.0.0.1:8000` で待ち受け、UNIXソケット `/run/website/app.sock` のアプリへプロキシする。 |
| `website` | このリポジトリの `Dockerfile` | アプリ本体。 |

- `nginx` と `website` は、ボリューム `website-run`(`/run/website`)でUNIXソケットを共有します。
- `website` のボリューム: `./.git`(読み取り専用。バージョン表示用)、`./public`(読み取り専用)、`./private`(読み書き)、`website-run`。`public` は読み取り専用でマウントします。この方針を維持してください。
- ログは `json-file`(10MB × 5ファイル)です。
- 必須の環境変数は `.env` に置きます(`.env.example` を参照): `CONET_PRIVATE_KEY`、`CONET_PRESHARED_KEY`(必須)、`CERT_CA_FINGERPRINT`(任意)。**`.env` の内容は読み出し・表示・コミットをしないでください。**
- `nginx.conf` は `X-Forwarded-For` を設定し、`127.0.0.1` を信頼します。アプリは `FORWARDED_ALLOW_IPS="*"` で動作します(アプリへ到達できるのはnginx経由のみという前提です)。この前提を崩す変更(アプリのポートの公開など)をしないでください。

### 開発(`docker-compose.dev.yml`)

`tools/start.sh --dev` と `tools/update.sh --dev` は `docker-compose.dev.yml` だけを指定します(`docker-compose.yml` とは重ねない、単独の構成です)。`website` だけを起動し、`8080:8080` を公開して `WEBSITE_DEV=1` で動かします。

Dockerを使わない場合は、次のコマンドで起動できます(`.claude/launch.json` の `website-dev` と同じ)。

```bash
WEBSITE_DEV=1 WEBSITE_TCP_PORT=8080 uv run nercone-website
```

### Dockerイメージ

- builder(`debian:bookworm-slim`)で `uv` を使い、`uv.lock` に従って依存関係を `--frozen --no-dev` でインストールします。
- 実行イメージは `gcr.io/distroless/base-debian12` です。builderから Python、`.venv`、CA証明書、`git` などをコピーします。
- ビルド引数 `PYTHON_VERSION`、`PACKAGES_VERSION`(DebianパッケージのIndexのハッシュ。変化時にキャッシュを無効化するためのもの)は `tools/start.sh` / `tools/update.sh` が計算して渡します。`docker compose build` を直接実行する場合は、これらを自分で渡す必要があります。

### 運用スクリプト

- `tools/start.sh [--dev]`: ビルドして `up -d` します。
- `tools/update.sh [--dev]`: `git pull` し、ビルドして `restart` と `up -d` を行います。
- `tools/png2jxl.sh`: PNGをJPEG XLへ変換する補助スクリプトです(`cjxl` が必要)。
- `tools/sounds/build.py`: `public/static/assets/sounds/` のサウンドを MIDI から生成します(`uv run tools/sounds/build.py`、FFmpeg が必要)。詳細は `.docs/sounds.md` を参照してください。

本番サーバーへの操作(デプロイ、再起動、`update.sh` の実行など)は、必ず人間に確認してから行ってください。

## 開発上の注意

- 依存関係は `uv` で管理します(`uv add` / `uv sync`)。`uv.lock` を更新したら一緒にコミット対象として報告してください。
- `public/static/assets/` 以下のCSS・JSは、`style.css` / `script.js` へバンドルされる構成です(`constants.py` の `Files.Bundles`、`helpers/bundle.py`)。生成される出力物ではなく、エントリ(`styles/index.css`、`scripts/index.js`)側を編集してください。
- `public/data/`、`data/`、`.env`、`private/` はGit管理外です。

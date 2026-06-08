---
title: nercone.devの設定
header_desc: このウェブサイトの設定
---

# nercone.dev の設定

nercone.devの動作を変更できます。
これらの設定はCookieを使用してブラウザ上に保存されます。

> [!WARNING]
> この機能はテスト段階です。自己責任でご使用ください。
>
> - この機能を使用すると、nercone.devの一部または全ての機能が正常に動作しなくなる場合があります。
> - この機能は予告なく変更、無効化または削除される場合があります。
> - 一部の問題はこのサイトのCookieやキャッシュなどをブラウザから削除することで解決できる場合があります。

<section id="apperance">
    <h2>外観</h2>
    <div class="flex">
        <b>テーマ</b>
        <div class="dropdown">
            <button class="dropdown-item">{{ options.get('dev.nercone.options.apperance.theme') }}</button>
            <div class="dropdown-menu">
                <a class="dropdown-item{% if options.get('dev.nercone.options.apperance.theme') == 'dark' %} is-active{% endif %}" href="?dev.nercone.options.apperance.theme=dark">dark</a>
                <a class="dropdown-item{% if options.get('dev.nercone.options.apperance.theme') == 'black' %} is-active{% endif %}" href="?dev.nercone.options.apperance.theme=black">black</a>
                <a class="dropdown-item{% if options.get('dev.nercone.options.apperance.theme') == 'light' %} is-active{% endif %}" href="?dev.nercone.options.apperance.theme=light">light</a>
            </div>
        </div>
    </div>
</section>

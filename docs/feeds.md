# Фиды: исходный фид, сборка пакетов и репозиторий ipk

Здесь две разные вещи:

- **исходный фид** — этот репозиторий (`wrtnavsegda`): Makefile пакетов (`halo`, `halo-mod-*`,
  `halo-metrics`, `opkg-repository`, …), их подключает SDK OpenWrt (`feeds.conf`);
- **фид ipk** (репозиторий opkg) — каталог собранных пакетов с подписанным индексом `Packages`,
  его раздаёт HTTP-сервер, а роутер получает пакеты через `opkg update` / `opkg install`.

Пример ниже — машина сборки Debian (`wrt-debian`, 192.168.105.82), SDK R50
(`~/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64`,
архитектура пакетов `arm_cortex-a7_neon-vfpv4`), nginx, роутер R50 на прошивке irzOS 1.2.

## 1. SDK и исходные фиды

`feeds.conf` SDK (пути — свои):

```
src-git base https://git.openwrt.org/openwrt/openwrt.git;openwrt-24.10
src-git packages https://git.openwrt.org/feed/packages.git;openwrt-24.10
…
src-link irz  /home/art/sdk24/irz-local        # пакеты iRZ, которых нет в фидах OpenWrt
src-link halo /home/art/Coding/wrtnavsegda     # этот репозиторий
```

- `src-link` — каталог на диске: правки видны сразу, без коммита.
- Новый пакет в фиде или новый фид — `./scripts/feeds update <фид>` и
  `./scripts/feeds install -p <фид> <пакет>` (пакет с тем же именем в другом фиде — `-f`).
- Обновить фиды OpenWrt — `./scripts/feeds update -a && ./scripts/feeds install -a`;
  версии библиотек должны совпадать с прошивкой (SDK — та же версия OpenWrt, 24.10.2).

### Пакеты iRZ, которых нет на buildbot

На buildbot лежат только пакеты, вошедшие в образ прошивки. Нужен ещё один пакет iRZ (пример —
`lighttpd-mod-proxy` к lighttpd 1.4.85 iRZ: плагин грузится только той же версией lighttpd,
штатный SDK — 1.4.79) — каталог пакета из `clean/packages` (ветка `devel-v24`, только чтение)
кладётся в `irz-local/<раздел>/<пакет>`, затем:

```sh
./scripts/feeds update irz && ./scripts/feeds install -f -p irz lighttpd
# в .config — только нужный подпакет: SDK с CONFIG_ALL=y включает все,
# остальные выключить явно ("# CONFIG_PACKAGE_lighttpd-mod-xxx is not set")
echo CONFIG_PACKAGE_lighttpd-mod-proxy=m >> .config && make defconfig
make package/feeds/irz/lighttpd/compile
```

Если исходник не скачивается (download.lighttpd.net отдавал только начало файла) — взять с
зеркала `https://sources.openwrt.org/<архив>`, сверить SHA-256 с `PKG_HASH` Makefile и положить в
`dl/`.

## 2. Сборка пакетов Halo

Исходник Halo — репозиторий donyx. Два способа:

- **из коммита** (выпуск): `PKG_SOURCE_VERSION` в `halo.mk` — коммит donyx, один на все пакеты
  Halo; после коммита в donyx — поднять его здесь. `make package/feeds/halo/<пакет>/compile`.
- **из рабочей копии** (разработка): `HALO_SRC=<каталог donyx> make …`; так собирает
  `scripts/router.sh ipk` donyx (сначала rsync рабочей копии и каталогов пакетов на машину сборки).

Версии:

- `PKG_RELEASE`: в сборке прошивки — `calc_pkg_release`; из рабочей копии — время сборки UTC
  (`ГГММДДччмм`, переменная `HALO_RELEASE`, `router.sh` ставит её одну на все пакеты сборки),
  иначе каждая сборка была бы `0.1-r1` и `opkg upgrade` новую не видел; из коммита вне прошивки — `1`.
- `HALO_SVELTE` — версия Svelte (проверяется при сборке). `halo` и `halo-preview` дают
  `halo-svelte-<версия>` и `halo-runtime-<HALO_RUNTIME>`, модули зависят от обоих.
  `HALO_RUNTIME` поднимать, когда модуль, собранный под новый рантайм, не заработает на прежнем
  Halo: новая общая библиотека (`LIB_ENTRIES` в `runtime.shared.ts` donyx), несовместимое
  изменение `@halo/ui`. Тогда пересобрать Halo и все модули.

Перед сборкой прежние ipk этих пакетов удалить из `bin/packages/<арх>/halo/` (`router.sh` делает
это сам): иначе в фид попадут обе версии.

## 3. Фиды ipk прямо из каталога сборки (основной способ)

Каждый фид SDK — уже готовый фид ipk: `bin/packages/<арх>/<фид>/` (`halo`, `irz`, `base`,
`packages`, `routing`, …). Нужны только индекс с подписью и HTTP-сервер, который смотрит в этот
каталог, — без копирования.

**Индекс и подпись делает SDK.** При `CONFIG_SIGNED_PACKAGES=y` `make package/index` пишет
`Packages`, `Packages.gz` и `Packages.sig` во все фиды `bin/packages/<арх>/`, подписывая ключом
`key-build` из корня SDK. Один раз — положить туда ключ фида (раздел 3а), дальше после сборки:

```sh
cd <SDK> && make package/index
```

(`scripts/router.sh ipk` donyx делает это сам.) Перед сборкой прежние ipk пакета удалить из
каталога фида — иначе в индексе обе версии (`router.sh` удаляет).

**nginx** — один `alias` на каталог архитектуры (`/etc/nginx/sites-available/default` или свой
блок, затем `sudo nginx -t && sudo systemctl reload nginx`):

```nginx
location /opkg/ {
    alias /home/art/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64/bin/packages/arm_cortex-a7_neon-vfpv4/;
    location ~ /Packages(\.gz|\.sig)?$ { add_header Cache-Control "no-store"; }
}
```

Фиды — `http://<машина сборки>/opkg/<фид>`. Домашний каталог закрыт (700): nginx (`www-data`)
нужно право прохода (`x`, без чтения списка) по каждому каталогу пути — ACL, один раз:

```sh
S=/home/art/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64
sudo setfacl -m u:www-data:x /home/art /home/art/sdk24-r50 $S $S/bin $S/bin/packages
```

Каталоги и файлы в `bin/packages/<арх>` SDK создаёт читаемыми для всех.

**Роутер** — строка на каждый нужный фид в `/etc/opkg/customfeeds.conf` и открытый ключ в
`/etc/opkg/keys` (раздел 5):

```
src/gz sdk_halo     http://192.168.105.82/opkg/halo
src/gz sdk_irz      http://192.168.105.82/opkg/irz
src/gz sdk_packages http://192.168.105.82/opkg/packages
```

Так любой пакет, собранный в SDK (`make package/feeds/<фид>/<пакет>/compile`), ставится на
роутер `opkg update && opkg install <пакет>`. Минусы: фид не подменяется целиком (во время
сборки индекс может не совпасть с файлами — для стенда разработки неважно); пакеты фидов
OpenWrt, собранные в SDK, на роутере предлагаются и как обновления пакетов прошивки — их, как и
фид `wrt_pkg`, ставить обдуманно.

## 3а. Ключ подписи

Тот же ключ подписывает и фиды каталога сборки (положить `key-build` и `key-build.pub` в корень SDK), и
фид-копию ниже.

## 3б. Фид-копия: публикация (запасной способ)

Отдельный фид с отбором пакетов и подменой целиком — копия в каталог HTTP-сервера.

Индекс фида строит `scripts/ipkg-make-index.sh` SDK, подпись — `usign` (ключ Ed25519; `opkg` на
роутере проверяет подпись индекса, `option check_signature` в `/etc/opkg.conf`), в индексе —
SHA-256 каждого пакета.

Создать ключ — один раз, на машине сборки (секретный ключ не уходит с неё):

```sh
S=~/sdk24-r50/openwrt-sdk-…/staging_dir/host/bin
mkdir -p ~/.config/opkg-feed && chmod 700 ~/.config/opkg-feed
$S/usign -G -s ~/.config/opkg-feed/key-build -p ~/.config/opkg-feed/key-build.pub -c "halo dev feed"
chmod 600 ~/.config/opkg-feed/key-build
$S/usign -F -p ~/.config/opkg-feed/key-build.pub     # отпечаток — имя файла ключа на роутере
```

Скрипт публикации — `scripts/opkg-publish` этого репозитория (на машине сборки — копия в `~/bin`; пути переопределяются окружением: `SDK`, `SRC`, `DST`, `KEY`, `EXTRA`), запускать после каждой сборки. Его суть:

```sh
#!/bin/sh
set -e
SDK=$HOME/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64
ARCH=arm_cortex-a7_neon-vfpv4
SRC=$SDK/bin/packages/$ARCH/halo           # пакеты фида halo
DST=/var/www/html/opkg/halo                # каталог HTTP-сервера
KEY=$HOME/.config/opkg-feed/key-build
# пакеты других фидов SDK, нужные пакетам halo и отсутствующие в фидах прошивки
EXTRA="irz/lighttpd-mod-proxy_*.ipk"
BIN=$SDK/staging_dir/host/bin
export PATH="$BIN:$PATH" MKHASH="$BIN/mkhash"
mkdir -p "$DST.new"
cp -p "$SRC"/*.ipk "$DST.new/"
for f in $EXTRA; do cp -p $SDK/bin/packages/$ARCH/$f "$DST.new/"; done
(cd "$DST.new" && "$SDK/scripts/ipkg-make-index.sh" . 2>/dev/null > Packages && gzip -9nc Packages > Packages.gz)
usign -S -m "$DST.new/Packages" -s "$KEY"
rm -rf "$DST.old"; [ -d "$DST" ] && mv "$DST" "$DST.old"; mv "$DST.new" "$DST"; rm -rf "$DST.old"
echo "published $(grep -c '^Package:' "$DST/Packages") packages to $DST"
```

Каталог подменяется целиком (`.new` → на место), клиенты не видят половину фида. Другой фид —
копия скрипта со своими `SRC`, `DST` и, по желанию, своим ключом.

## 4. HTTP-сервер (nginx)

opkg качает только по `http(s)://`, `ftp://`, `file://` — не по ssh/sftp. Штатный nginx Debian уже
раздаёт `/var/www/html`; каталог фида — во владение пользователя сборки (один раз, sudo):

```sh
sudo apt install nginx
sudo install -d -o art -g art /var/www/html/opkg
```

Фид — `http://<машина сборки>/opkg/halo`. Отдельный сервер или порт — свой блок nginx
(`/etc/nginx/sites-available/opkg`, ссылка в `sites-enabled`, `sudo nginx -t && sudo systemctl reload nginx`):

```nginx
server {
    listen 8080;
    root /srv/opkg;              # владелец — пользователь сборки
    autoindex on;                # список файлов — для людей, opkg он не нужен
    location / {
        try_files $uri $uri/ =404;
    }
    # индексы не кэшировать: после публикации роутер должен видеть новый
    location ~ /Packages(\.gz|\.sig)?$ {
        add_header Cache-Control "no-store";
    }
}
```

Домашний каталог (`/home/<user>`, права 700) nginx не читает — поэтому копия в `/var/www/html`
или `/srv`, а не ссылка на каталог SDK. Файрвол машины сборки должен пускать роутеры на порт.

## 5. Роутер: подключить фид

```sh
# открытый ключ — имя файла = отпечаток ключа
scp -O ~/.config/opkg-feed/key-build.pub root@<роутер>:/etc/opkg/keys/<отпечаток>
# фид — в customfeeds.conf (или схемой /system/repository пакета opkg-repository)
echo 'src/gz halo-dev http://192.168.105.82/opkg/halo' >> /etc/opkg/customfeeds.conf
opkg update            # "Signature check passed" у фида
opkg install halo-preview halo-mod-software …   # дальше — opkg upgrade
```

`scp` без `-O` идёт по SFTP, а он на прошивке iRZ ограничен временным хранилищем
(`/storage/temp`, только имена файлов) — для произвольного пути нужен `-O`.

### Фиды прошивки iRZ

`irzos_oss`, `irzos_pkg`, `irzos_wrt` в `/etc/opkg/distfeeds.conf` прошивки указывают на
downloads.openwrt.org, где их нет. Рабочие — фиды сборки на buildbot (подписаны ключом сборки
iRZ, он уже есть в `/etc/opkg/keys`), номер сборки — тот, что стоит на роутере:

```
src/gz irzos_oss http://buildbot.radiofid.ru/artifacts/DEVELOP/irzOS/<плата>/<сборка>/ipk/oss
src/gz irzos_pkg http://buildbot.radiofid.ru/artifacts/DEVELOP/irzOS/<плата>/<сборка>/ipk/pkg
src/gz irzos_wrt http://buildbot.radiofid.ru/artifacts/DEVELOP/irzOS/<плата>/<сборка>/ipk/wrt
```

(номер сборки — по `manifest.json` buildbot: каталог, где лежит образ с версией прошивки).

### После обновления прошивки

sysupgrade сохраняет настройки, а не пакеты:

- пакеты, поставленные поверх прошивки (Halo, модули, `opkg-repository`, …), снимаются —
  поставить заново из фида;
- `distfeeds.conf` — снова из прошивки: фиды iRZ перевести на новый номер сборки;
- `customfeeds.conf` и `/etc/opkg/keys` сохраняются;
- `/root/.ssh` не сохраняется (сохраняется `/home`): добавить `/root/.ssh/` в `/etc/sysupgrade.conf`.

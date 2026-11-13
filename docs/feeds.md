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

Исходник Halo — репозиторий donyx. Какой код попадает в пакет (`halo.mk`):

- **последний коммит ветки** (по умолчанию): `git ls-remote` ветки `HALO_BRANCH` (`main`) при
  разборе Makefile — нужен доступ машины сборки к GitHub по ssh. Хеш входит в имя архива в
  `dl/`, поэтому новый коммит SDK скачивает сам (с `PKG_SOURCE_VERSION:=main` архив в `dl/` не
  обновлялся бы). Нет доступа — закреплённый `HALO_PINNED` с предупреждением;
- **закреплённый коммит** `HALO_PINNED` — в сборке прошивки (`FW_MAJOR`), для воспроизводимости;
- **явный коммит** — `HALO_COMMIT=<хеш> make …`, другая ветка — `HALO_BRANCH=<ветка>`;
- **рабочая копия** (разработка, незакоммиченное): `HALO_SRC=<каталог donyx> make …`; так собирает
  `scripts/router.sh ipk` donyx (сначала rsync рабочей копии и каталогов пакетов на машину сборки).

Обновить пакеты из последних исходников — `scripts/build-feed` этого репозитория (без списка
пакетов — актуальные из `scripts/feed-packages`: Halo и модули, halo-metrics, opkg-repository,
horizon-uc, aurora-uc; новый пакет фида — дописать туда; в аргументах — имена пакетов или
каталогов: `halo-preview`, `zenith-uc`, `halo-metrics-collectd` собирают свой каталог), на машине
сборки (git pull клона, feeds update, clean, сборка всех вместе, подписанные индексы):

```sh
~/Coding/wrtnavsegda/scripts/build-feed ~/sdk24-r50/openwrt-sdk-…            # всё из scripts/feed-packages
~/Coding/wrtnavsegda/scripts/build-feed ~/sdk24-r50/openwrt-sdk-… halo-mod-software
~/Coding/wrtnavsegda/scripts/build-feed ~/sdk24-r50/openwrt-sdk-… halo-preview   # = каталог halo: halo и halo-preview
```

Типовой цикл — правка Halo или модуля → пакеты на роутере:

1. закоммитить и запушить donyx (и wrtnavsegda, если менялись Makefile): собирается то, что
   лежит в `main` на GitHub;
2. на машине сборки:

   ```sh
   ssh wrt-debian
   ~/Coding/wrtnavsegda/scripts/build-feed ~/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64
   ```

   или одной командой с рабочей машины —
   `ssh wrt-debian '~/Coding/wrtnavsegda/scripts/build-feed ~/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64 halo-mod-software'`;
3. на роутере — `opkg update && opkg upgrade` (или «Update lists» и «Upgrade» на странице
   Software в Halo).

Вывод запуска (два пакета, около 1,5 мин; предупреждения `Config-build.in … defaults for
choice values not supported` — штатные для SDK, не ошибка):

```
build-feed: halo-mod-dash-clock opkg-repository
…
build-feed: built in /home/art/sdk24-r50/openwrt-sdk-…/bin/packages/arm_cortex-a7_neon-vfpv4/halo:
  halo-mod-dash-clock_0.1-r2611130926_all.ipk
  opkg-repository_0.1-r3_all.ipk
```

Номер выпуска (`r2611130926`) — время сборки, поэтому `opkg upgrade` на роутере видит новую
сборку; у пакетов со своим `PKG_RELEASE` (`opkg-repository`) — их номер: новую версию даёт его
подъём в Makefile. `<пакет>: no new ipk (see the build log)` — пакет не собрался: запустить для
него ещё раз и смотреть вывод `make` выше (сборка остальных при этом идёт до конца, `make -k`,
а скрипт завершается ошибкой; подробный вывод одного пакета —
`make package/feeds/halo/<каталог>/compile V=s` в SDK). Прежние версии собранных пакетов из фида удаляются
(по имени пакета, так что и `halo-preview`, `zenith-uc`, `halo-metrics-collectd`). Без доступа к GitHub Halo собирается из закреплённого
коммита `HALO_PINNED` (предупреждение в выводе). Свой коммит или ветка —
`HALO_COMMIT=<хеш> scripts/build-feed <SDK> …`, `HALO_BRANCH=<ветка> scripts/build-feed <SDK> …`.

То же руками:

```sh
cd ~/Coding/wrtnavsegda && git pull     # Makefile пакетов (если менялись)
cd <SDK>
./scripts/feeds update halo            # только при новых пакетах в фиде
A=bin/packages/arm_cortex-a7_neon-vfpv4/halo
rm -f $A/halo_*_all.ipk $A/halo-preview_*_all.ipk $A/halo-mod-*_all.ipk
make package/feeds/halo/halo/clean package/feeds/halo/halo-mod-software/clean …
make -j$(nproc) package/feeds/halo/halo/compile package/feeds/halo/halo-mod-software/compile …
make package/index                      # индексы с подписью — роутеры видят сразу
```

Halo и модули собирать вместе, одной командой: модули собираются под рантайм своей сборки Halo.
`clean` — отдельной командой и до `compile`: цели одной командной строки `make -j` выполняет
вперемешку, и `clean` пакета может выполниться после его же `compile` и удалить только что
собранный ipk (так
13.11 из фида пропали halo, модули и opkg-repository).

Версии:

- `PKG_RELEASE`: в сборке прошивки — `calc_pkg_release`; из рабочей копии — время сборки UTC
  (`ГГММДДччмм`, переменная `HALO_RELEASE`, `router.sh` ставит её одну на все пакеты сборки),
  иначе каждая сборка была бы `0.1-r1` и `opkg upgrade` новую не видел; так же — из последнего
  коммита ветки; из явного коммита вне прошивки — `1`.
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
`key-build` из корня SDK. SDK при первой сборке создаёт свой ключ — его роутеры не знают; один раз
заменить его ключом фида (раздел 3а), сохранив прежний:

```sh
cd <SDK>
mv key-build key-build.sdk-orig && mv key-build.pub key-build.pub.sdk-orig
install -m 600 ~/.config/opkg-feed/key-build key-build
install -m 644 ~/.config/opkg-feed/key-build.pub key-build.pub
make package/index        # дальше — после каждой сборки
```

(`scripts/router.sh ipk` donyx вызывает `make package/index` сам.) Перед сборкой прежние ipk
пакета удалить из каталога фида — иначе в индексе обе версии (`router.sh` удаляет).

**nginx — без sudo и без правки конфига.** Каталог `/var/www/html/opkg` принадлежит
пользователю сборки (раздел 4), а nginx по умолчанию ходит по символическим ссылкам — достаточно
ссылки на каталог архитектуры:

```sh
S=/home/art/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64
ln -sfn $S/bin/packages/arm_cortex-a7_neon-vfpv4 /var/www/html/opkg/sdk
```

Фиды — `http://<машина сборки>/opkg/sdk/<фид>`. Домашний каталог закрыт (700): nginx
(`www-data`) нужно право прохода (`x`, без чтения списка файлов) по каждому каталогу пути. Это
ACL, его ставит сам владелец каталогов (sudo не нужен), один раз:

```sh
setfacl -m u:www-data:x /home/art /home/art/sdk24-r50 $S $S/bin $S/bin/packages
```

Каталоги и файлы в `bin/packages/<арх>` SDK создаёт читаемыми для всех. Другая архитектура (SDK
R2) — своя ссылка (`/var/www/html/opkg/sdk-mipsel`) и ACL на путь её SDK. Вместо ссылки можно
`alias` в конфиге nginx (`location /opkg/sdk/ { alias $S/bin/packages/<арх>/; }`) — тогда нужен
sudo для конфига.

**Роутер** — строка на каждый нужный фид в `/etc/opkg/customfeeds.conf` и открытый ключ в
`/etc/opkg/keys` (раздел 5):

```
src/gz sdk_halo     http://192.168.105.82/opkg/sdk/halo
src/gz sdk_irz      http://192.168.105.82/opkg/sdk/irz
src/gz sdk_packages http://192.168.105.82/opkg/sdk/packages
src/gz sdk_base     http://192.168.105.82/opkg/sdk/base
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

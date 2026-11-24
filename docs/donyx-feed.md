# Donyx-фид Halo (Donyx iRM, dnxOS 1.2)

Ветка `donyx` — отдельная сборка Halo для Donyx iRM (`donyx,irm`, mediatek/filogic,
aarch64, dnxOS 1.2 / OpenWrt 24.10). Она не меняет irz-фид на Debian:

- исходный фид — этот репозиторий, ветка `donyx` (клон `~/Coding/wrtnavsegda-donyx`);
- SDK — отдельная копия R50 SDK (`~/sdk24-irm`), чтобы не заменить пакеты и индекс
  irz-фида в `~/sdk24-r50`;
- ipk-фид — `/var/www/html/opkg/donyx`, отдельно от `/var/www/html/opkg/halo`.

Halo собирается из последнего коммита ветки `split` репозитория donyx
(`HALO_BRANCH=split`); бренд включается `DONYX=1` — оформление Donyx, SSL-конфиг,
ссылки на прошивки donyx.com и точка GPS по карте Donyx. Все пакеты Halo — `all`,
поэтому SDK R50 подходит и для aarch64-платы; архитектурные зависимости
(`lighttpd`, `ttyd`, …) берутся из прошивки Donyx.

## Один раз на Debian

```sh
git clone https://github.com/artnavsegda/wrtnavsegda ~/Coding/wrtnavsegda-donyx
cd ~/Coding/wrtnavsegda-donyx
git checkout donyx

# отдельный SDK: копия R50, чтобы irz-фид и его индекс не менялись
cp -a ~/sdk24-r50/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64 \
      ~/sdk24-irm/
S=~/sdk24-irm/openwrt-sdk-24.10.2-ipq40xx-generic_gcc-13.3.0_musl_eabi.Linux-x86_64
sed -i 's|^src-link halo .*|src-link halo /home/art/Coding/wrtnavsegda-donyx|' "$S/feeds.conf"
rm -f "$S"/bin/packages/*/halo/*.ipk "$S"/bin/packages/*/halo/Packages*

# публикатор из репозитория (понимает DST/SRC/EXTRA; старый ~/bin/opkg-publish — в бэкап)
cp -p ~/bin/opkg-publish ~/bin/opkg-publish.irz 2>/dev/null || true
install -m 755 scripts/opkg-publish ~/bin/opkg-publish
```

## Сборка и публикация

```sh
cd ~/Coding/wrtnavsegda-donyx
scripts/build-feed-donyx
```

Скрипт собирает `halo` (оба варианта), модули и `halo-metrics` с `DONYX=1`,
`HALO_BRANCH=split`, общим номером выпуска, и публикует подписанный индекс в
`/var/www/html/opkg/donyx`. Проверка:

```sh
curl -s http://192.168.245.248/opkg/donyx/Packages | grep -E '^(Package|Version|Architecture):' | head
```

Фид: `http://192.168.245.248/opkg/donyx` (nginx, тот же ключ, что у irz-фида).

## Установка на Donyx iRM (bolt-on)

Ключ и фид — один раз:

```sh
# ключ: имя файла — отпечаток; на Debian:
usign -F -p ~/.config/opkg-feed/key-build.pub
# scp -O (SFTP в прод-sshd может быть ограничен)
scp -O ~/.config/opkg-feed/key-build.pub root@<irm>:/etc/opkg/keys/<отпечаток>
echo 'src/gz halo_donyx http://192.168.245.248/opkg/donyx' >> /etc/opkg/customfeeds.conf
opkg update
```

Рядом со штатной Авророй (рекомендуется для первых прогонов, `/halo/`):

```sh
opkg install halo-preview
opkg install halo-metrics halo-mod-software halo-mod-firmware \
    halo-mod-console halo-mod-dash-hbar halo-mod-dash-clock
# по желанию, если есть приёмник GPS:
opkg install halo-mod-dash-gps
# альтернативы: halo-mod-dash-gauge вместо -hbar, halo-mod-dash-webgl вместо -load
```

Вместо Авроры (Halo на `/`; сначала удалить `aurora` — пакеты конфликтуют):

```sh
opkg remove aurora
opkg install halo
```

Проверка:

```sh
opkg list-installed | grep -E '^(halo|halo-)'
curl -sk -I https://127.0.0.1/halo/ | head        # для halo-preview
```

`halo-preview` зависит от `aurora`; `halo` конфликтует с ней. Модули ставятся на
любой вариант. `halo-mod-console` требует `lighttpd-mod-proxy`/`ttyd`/`openssh-client`
(в dnxOS они должны быть из прошивки; если нет — поставить из фидов OpenWrt).
`halo-mod-dash-gps` в donyx-сборке зависит от `dnxos-gpsd`; без GPS-пакета его не
ставить.

## Обновление и удаление

```sh
opkg update && opkg upgrade          # видит новый номер выпуска
# или точечно, в том числе та же сборка:
opkg install --force-reinstall halo-preview halo-mod-software ...
```

Удаление — как в [install.md](install.md): модули, затем `halo-preview` или `halo`
(и вернуть `aurora`, если Halo ставился вместо неё).

## Отличия от irz-фида

- `DONYX=1`: тема Donyx, SSL-конфиг `ssl-config-dnx`, `FIRMWARE_URL_DNX`,
  GPS-точка Donyx; `check-brand donyx` проверяет, что irz-оформления нет.
- Отдельный SDK и отдельный каталог фида — irz-роутеры, подключённые к
  `/opkg/halo`, не получают donyx-пакеты.
- `lighttpd-mod-proxy` из irz-фида не копируется: это arm-пакет R50, на iRM
  (aarch64) он не подходит; нужен пакет из прошивки/фидов Donyx.

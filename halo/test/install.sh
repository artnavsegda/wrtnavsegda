#!/bin/sh
# Проверка установки пакетов Halo (halo-preview рядом с aurora, halo вместо aurora, модули на
# каждом) в контейнере OpenWRT 24.10 (образ стенда horizon-uc): в /root/ipk — собранные halo*.ipk,
# прод-aurora и заглушка irzos-gpsd, в /root/base — прод-lighttpd и openssl 3.5 (имитация
# прошивки: прод-lighttpd работает от root). Запуск: docker exec <контейнер> sh /root/install.sh
cd /root/ipk || exit 1
FAILS=0
ok()   { echo "  ok   $*"; }
bad()  { echo "  FAIL $*"; FAILS=$((FAILS+1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
# HTTP-код: uclient-fetch -S печатает заголовки ответа
code() { printf 'GET %s HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n' "$1" | openssl s_client -quiet -connect 127.0.0.1:443 2>/dev/null | head -1 | cut -d' ' -f2; }
http() { c=$(code "$1"); if [ "$c" = "$2" ]; then ok "GET $1 -> $c"; else bad "GET $1 -> $c (want $2)"; fi; }
inst() { # пакеты без --force: ошибка opkg — провал
	out=$(opkg install "$@" 2>&1); rc=$?
	if [ $rc -eq 0 ] && ! echo "$out" | grep -qiE "^ \* |error|collected errors"; then ok "opkg install $*"; else bad "opkg install $* (rc $rc)"; echo "$out" | grep -iE "^ \* |error" | head -8 | sed 's/^/        /'; fi
}
rem() {
	out=$(opkg remove "$@" 2>&1); rc=$?
	if [ $rc -eq 0 ] && ! echo "$out" | grep -qiE "^ \* |error"; then ok "opkg remove $*"; else bad "opkg remove $* (rc $rc)"; echo "$out" | head -8 | sed 's/^/        /'; fi
}
lighttpd_ok() { /usr/sbin/lighttpd -tt -f /var/run/lighttpd/lighttpd.conf >/dev/null 2>&1 && pidof lighttpd >/dev/null; }
MODS="halo-mod-software_*.ipk halo-mod-firmware_*.ipk halo-mod-console_*.ipk halo-mod-dash-hbar_*.ipk halo-mod-dash-clock_*.ipk halo-mod-dash-gps_*.ipk"
MODNAMES="halo-mod-software halo-mod-firmware halo-mod-console halo-mod-dash-hbar halo-mod-dash-clock halo-mod-dash-gps"

modules_checks() { # $1 — корень Halo в URL ("/halo/" или "/")
	B="$1"
	check "manifest: preload hardware" "gunzip -c /usr/share/halo/modules/manifest.js | grep -q 'dashboard/hardware'"
	check "manifest: clock не preload" "! gunzip -c /usr/share/halo/modules/manifest.js | grep -q 'dashboard/clock'"
	http "${B}modules/manifest.js" 200
	http "${B}modules/software/index.js" 200
	http "${B}modules/dashboard/hardware/index.js" 200
	http "${B}modules/dashboard/gps/index.js" 200
	http "${B}runtime/ui.js" 200
	# CGI модуля подключён и запускается: GET он отвергает (только POST)
	http "/script/software/list" 405
	check "схемы модулей" "[ -f /usr/share/horizont/schema/system/software.json ] && [ -f /usr/share/horizont/schema/system/console.json ]"
	check "firmwareUrl подставлен" "grep -q 'https://faq.irz.net/' /usr/share/horizont/schema/system/firmware.json"
	check "раздел сводки clock" "[ -f /usr/share/horizont/script/dashboard.d/0150-clock.uc ]"
	check "lighttpd: конфиг и процесс" "lighttpd_ok"
	check "lighttpd: halo.d подключён" "grep -q 'halo.d' /var/run/lighttpd/lighttpd.conf"
	check "консоль: ttyd на lo:7682" "netstat -ltn | grep -q '127.0.0.1:7682'"
	check "штатный ttyd выключен" "! netstat -ltn | grep -q ':7681 '"
	printf 'GET /halo-console/ws HTTP/1.1\r\nHost: x\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Protocol: tty\r\n\r\n' > /tmp/ws.req
	(sleep 5 | cat /tmp/ws.req - | openssl s_client -quiet -connect 127.0.0.1:443 > /tmp/ws.out 2>/dev/null) & sleep 3; kill $! 2>/dev/null
	c=$(head -1 /tmp/ws.out)
	case "$c" in *101*) ok "WebSocket консоли -> 101" ;; *) bad "WebSocket консоли -> $c" ;; esac
	# альтернатива hardware: кольца поверх полосок не ставятся
	if opkg install halo-mod-dash-gauge_*.ipk >/dev/null 2>&1; then bad "dash-gauge поставился поверх dash-hbar"; else ok "dash-gauge поверх dash-hbar — отказ"; fi
}

echo "== база: прод-aurora поверх lighttpd стенда (имитация прошивки)"
grep -q "^arch aarch64_cortex-a53" /etc/opkg.conf || printf 'arch all 1\narch noarch 1\narch aarch64_generic 10\narch aarch64_cortex-a53 20\n' >> /etc/opkg.conf
# прод-lighttpd (работает от root, как в прошивке) и openssl 3.5 к нему
opkg install --force-reinstall --force-overwrite --nodeps /root/base/*.ipk >/dev/null 2>&1
opkg install --force-overwrite --nodeps aurora_*.ipk >/dev/null 2>&1 && /etc/init.d/lighttpd restart; sleep 2
check "aurora на /" "[ \"\$(code /)\" = 200 ] && [ -d /usr/share/aurora ]"
opkg update >/dev/null 2>&1
# заглушка пакета gpsd (на стенде нет приёмника)
check "заглушка irzos-gpsd" "opkg install ./irzos-gpsd_*.ipk >/dev/null 2>&1"
# libwebsockets-openssl (mosquitto) мешает ttyd (libwebsockets-full, он же PROVIDES -openssl)
opkg remove --force-depends libwebsockets-openssl >/dev/null 2>&1

echo "== вариант 1: halo-preview рядом с aurora"
inst halo-preview_*.ipk
http "/halo/" 200
http "/" 200
check "шаблон aurora: include halo.d" "grep -qxF 'include \"/etc/lighttpd/halo.d/*.conf\"' /etc/lighttpd/template.conf"
inst $MODS
check "CGI software в корне aurora" "[ -L /usr/share/aurora/script/software ]"
modules_checks /halo/
rem $MODNAMES
check "ссылка CGI убрана" "[ ! -e /usr/share/aurora/script/software ] && [ ! -L /usr/share/aurora/script/software ]"
check "манифест пуст" "! gunzip -c /usr/share/halo/modules/manifest.js | grep -q 'dashboard/'"
rem halo-preview
check "шаблон aurora без halo.d" "! grep -q 'halo.d' /etc/lighttpd/template.conf"
check "lighttpd после удаления" "lighttpd_ok"
http "/" 200

echo "== вариант 2: halo вместо aurora"
rem aurora
inst halo_*.ipk
check "lighttpd: включён" "ls /etc/rc.d/ | grep -q lighttpd"
http "/" 200
check "корень — Halo" "grep -q 'modules/manifest.js' /usr/share/halo/index.html"
inst $MODS
modules_checks /
rem $MODNAMES
rem halo
check "после halo ничего не осталось" "[ -z \"\$(find /usr/share/halo \( -type f -o -type l \) 2>/dev/null)\" ]"
echo "== итог: $FAILS ошибок"

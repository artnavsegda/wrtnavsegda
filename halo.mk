# Общее для пакетов Halo (halo, halo-preview) и его модулей (halo-mod-*): подключается в их
# Makefile после rules.mk и fw-version.mk, до package.mk.
#
# Исходник — один репозиторий и один коммит (donyx, ветка main — прод-протокол horizont):
# модули собираются под общий рантайм (Svelte и @halo/ui) именно этой сборки Halo. Новый
# коммит — меняется здесь, у всех пакетов сразу.
# Отладка: собрать из рабочей копии вместо коммита — HALO_SRC=<каталог donyx> make …
# (USE_SOURCE_DIR в командной строке подменил бы исходники и всем зависимостям)

PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
# номер выпуска: в сборке прошивки — calc_pkg_release; сборка из рабочей копии (HALO_SRC) —
# время сборки UTC (ГГММДДччмм), иначе opkg считает новую сборку той же версией и
# opkg upgrade (и обновления в halo-mod-software) её не видят; HALO_RELEASE — задать явно
# (один на всю сборку: router.sh ipk ставит его сам); сборка коммита вне прошивки — 1
ifneq ($(HALO_SRC),)
  ifeq ($(HALO_RELEASE),)
    HALO_RELEASE:=$(shell date -u +%y%m%d%H%M)
  endif
endif
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),$(or $(HALO_RELEASE),1))

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@github.com:artnavsegda/donyx.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=41fbcfe9130d56245448e8abc5c49ce1f5da294e
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

ifneq ($(HALO_SRC),)
  USE_SOURCE_DIR:=$(HALO_SRC)
endif

PKG_MAINTAINER:=iRZ Electronics <irz.net>

# общий рантайм Halo и модулей: Svelte этой версии (как в package.json donyx, проверяется при
# сборке). halo и halo-preview дают виртуальный пакет halo-svelte-<версия> (PROVIDES), модуль
# зависит от него (EXTRA_DEPENDS) — ставится на любой из двух вариантов Halo
HALO_SVELTE:=5.57.3
# версия рантайма Halo для модулей: halo и halo-preview дают halo-runtime-<N>, модуль зависит от
# него. Поднимать, когда модуль, собранный под новый рантайм, не заработает на прежнем Halo:
# новая общая библиотека (LIB_ENTRIES в runtime.shared.ts donyx), несовместимое изменение
# @halo/ui. 2 — общий @tanstack/svelte-table в рантайме (runtime/tanstack-svelte-table.js)
HALO_RUNTIME:=2

# зависимости node: общие (Svelte, Vite) и, если у модуля свой package.json, — его библиотеки
define Halo/Npm
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
endef

# сборка модуля modules/<каталог>: *.js.gz/*.css.gz — под исходными именами (lighttpd Halo
# отдаёт .js/.css с Content-Encoding: gzip)
define Halo/ModuleCompile
	$(call Halo/Npm)
	if [ -f $(PKG_BUILD_DIR)/modules/$(1)/package.json ]; then \
		cd $(PKG_BUILD_DIR)/modules/$(1) && npm ci --no-audit --no-fund; \
	fi
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/$(1)/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/$(1)/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

# модуль Halo: от Halo — только рантайм нужной версии (halo или halo-preview)
define Halo/ModuleDefault
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE), halo-runtime-$(HALO_RUNTIME)
endef

# манифест модулей и (в варианте рядом с aurora) ссылки на CGI модулей — после установки и
# удаления любого модуля
define Halo/Modules
[ -f "$${IPKG_INSTROOT}/usr/libexec/halo-modules" ] && sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
endef

# horizont перечитывает дерево схем (пункт меню схема-модуля появляется и пропадает вместе с
# пакетом): reload:all прод-horizont новые файлы схем не загружает, нужен сброс — @reset по
# внутреннему протоколу 127.0.0.1:65500. Код — прямо в скрипте: в postrm файлов модуля уже нет
define Halo/ResetSchemas
[ -n "$${IPKG_INSTROOT}" ] || ucode -e 'import * as socket from "socket"; import {pack} from "struct"; let s = socket.connect("127.0.0.1", 65500, {family: socket.AF_INET, socktype: socket.SOCK_STREAM}); if (s) { let r = sprintf("%J", {type: "@reset", path: "/", user: "root", data: {}}); s.setopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, {sec: 10, usec: 0}); s.send(pack("<L", length(r)) + r); s.recv(4); s.close(); }' 2>/dev/null
endef

# настройки веб-сервера от модулей: /etc/lighttpd/halo.d/*.conf (его подключают шаблоны
# lighttpd halo и — строкой, которую ставит halo-modules, — aurora); после них — перезапуск
define Halo/RestartWeb
[ -n "$${IPKG_INSTROOT}" ] || /etc/init.d/lighttpd restart
endef

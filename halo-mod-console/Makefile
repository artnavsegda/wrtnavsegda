include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Схема-модуль Halo «console»: SSH-консоль роутера в браузере. Клиент — xterm.js (свои
# библиотеки модуля, modules/console/package.json), на роутере — ttyd только на lo за lighttpd
# (WebSocket /halo-console/ws, mod_proxy), в сеансе — ssh на этот же роутер: вход, права и
# ip-lock — как у обычного ssh. Схема /system/console со ссылкой на модуль ("$module").
PKG_NAME:=halo-mod-console
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

# исходник — тот же репозиторий, что у halo (modules/console), и тот же коммит: модуль
# собран под рантайм этой сборки halo
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@github.com:artnavsegda/donyx.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=cbe5e5c2e0d6b350a70c7c9589cf57b0aabfebf0
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

# версия Svelte, под которую собран модуль: рантайм этой версии даёт пакет halo (PROVIDES)
HALO_SVELTE:=5.57.3

define Package/$(PKG_NAME)
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
	TITLE:=Halo module: SSH console
	DEPENDS:=+halo +ttyd +lighttpd-mod-proxy +openssh-client
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE)
endef

define Package/$(PKG_NAME)/description
	Halo page System / Console: SSH console of the router (xterm.js, ttyd)
endef

# сжатые *.js/*.css — под исходными именами (lighttpd отдаёт их с Content-Encoding: gzip)
define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	cd $(PKG_BUILD_DIR)/modules/console && npm ci --no-audit --no-fund
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/console/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/console/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/console
	$(CP) $(PKG_BUILD_DIR)/modules/console/dist/* $(1)/usr/share/halo/modules/console/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/console/schema/system/console.json $(1)/usr/share/horizont/schema/system/
	$(INSTALL_DIR) $(1)/usr/libexec $(1)/etc/init.d $(1)/etc/lighttpd/conf.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/console/backend/libexec/halo-console $(1)/usr/libexec/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/console/backend/init.d/halo-console $(1)/etc/init.d/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/console/backend/lighttpd/50-halo-console.conf $(1)/etc/lighttpd/conf.d/
endef

# horizont перечитывает дерево схем — пункт меню появляется и пропадает вместе с пакетом.
# reload:all прод-horizont новые файлы схем не загружает: нужен сброс (@reset по внутреннему
# протоколу 127.0.0.1:65500). Код — прямо в скрипте: в postrm файлов модуля уже нет
define Halo/ResetSchemas
ucode -e 'import * as socket from "socket"; import {pack} from "struct"; let s = socket.connect("127.0.0.1", 65500, {family: socket.AF_INET, socktype: socket.SOCK_STREAM}); if (s) { let r = sprintf("%J", {type: "@reset", path: "/", user: "root", data: {}}); s.setopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, {sec: 10, usec: 0}); s.send(pack("<L", length(r)) + r); s.recv(4); s.close(); }' 2>/dev/null
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
# штатная служба пакета ttyd — вход /bin/login на всех адресах (7681): выключить, консоль —
# только своя, на lo (7682) за lighttpd
[ -x /etc/init.d/ttyd ] && { /etc/init.d/ttyd stop; /etc/init.d/ttyd disable; }
/etc/init.d/halo-console enable
/etc/init.d/halo-console restart
/etc/init.d/lighttpd restart
$(Halo/ResetSchemas)
exit 0
endef

define Package/$(PKG_NAME)/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/halo-console stop
/etc/init.d/halo-console disable
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/lighttpd restart
$(Halo/ResetSchemas)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

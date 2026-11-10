include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль Halo «software»: установка, обновление и удаление пакетов (как Software в LuCI).
# Каждый модуль Halo — свой пакет: схема со ссылкой на модуль ("$module"), сборка модуля
# (Svelte и @halo/ui — из общего рантайма пакета halo) и CGI-скрипты его API.
PKG_NAME:=halo-mod-software
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

# исходник — тот же репозиторий, что у halo (modules/software), и тот же коммит: модуль
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
	TITLE:=Halo module: software packages
	DEPENDS:=+halo
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE)
endef

define Package/$(PKG_NAME)/description
	Halo page System / Software: installed packages, upload, install, update and remove
endef

# сжатые *.js/*.css — под исходными именами (lighttpd отдаёт их с Content-Encoding: gzip)
define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/software/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/software/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/software
	$(CP) $(PKG_BUILD_DIR)/modules/software/dist/* $(1)/usr/share/halo/modules/software/
	$(INSTALL_DIR) $(1)/usr/share/halo/script/software
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/software/backend/script/software/* $(1)/usr/share/halo/script/software/
	$(INSTALL_DIR) $(1)/usr/share/ucode/halo
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/software/backend/ucode/halo/software.uc $(1)/usr/share/ucode/halo/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/software/schema/system/software.json $(1)/usr/share/horizont/schema/system/
endef

# horizont перечитывает дерево схем — пункт меню появляется и пропадает вместе с пакетом.
# reload:all прод-horizont новые файлы схем не загружает: нужен сброс (@reset по внутреннему
# протоколу 127.0.0.1:65500). Код — прямо в скрипте: в postrm модуля halo.software уже нет
define Halo/ResetSchemas
ucode -e 'import * as socket from "socket"; import {pack} from "struct"; let s = socket.connect("127.0.0.1", 65500, {family: socket.AF_INET, socktype: socket.SOCK_STREAM}); if (s) { let r = sprintf("%J", {type: "@reset", path: "/", user: "root", data: {}}); s.setopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, {tv_sec: 10, tv_usec: 0}); s.send(pack("<L", length(r)) + r); s.recv(4); s.close(); }' 2>/dev/null
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
$(Halo/ResetSchemas)
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
$(Halo/ResetSchemas)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

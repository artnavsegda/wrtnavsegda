include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Веб-интерфейс Aurora (Vue 3 + Vite) для прод-прошивки (irzOS 1.2, horizont) —
# локальный вариант корпоративного aurora-фида (irzos-feeds/aurora): Vue 2 → Vue 3,
# webpack → Vite. Отличия от корпоративного: сборка — npm run build (dist/, уже с
# gzip-in-place через postbuild), icons.js — в репозитории (с import Iconify),
# пересобирать не нужно. Сборка из рабочей копии: AURORA_SRC=<каталог aurora> make …;
# иначе — закреплённый коммит ветки vue3.
PKG_NAME:=aurora
# Вне сборки прошивки — версия выше продовой (0.1 dev / 1.2 release), чтобы opkg
# апгрейдил установленный aurora (Vue 2, 0.1-r11) на этот (Vue 3), а не считал даунгрейдом
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),1.3)
# номер выпуска: в сборке прошивки — calc_pkg_release; из рабочей копии (AURORA_SRC) —
# время сборки UTC, иначе opkg не увидит пересобранный пакет как новый
ifneq ($(AURORA_SRC),)
  PKG_RELEASE:=$(shell date -u +%y%m%d%H%M)
else
  PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)
endif

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@gitlab.radiofid.ru:Routers/Developing/zos/aurora.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=825d5ca557e7f0f8f3be73363c5391ea8d388149
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

ifneq ($(AURORA_SRC),)
  USE_SOURCE_DIR:=$(AURORA_SRC)
endif

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
	TITLE:=irzOS web interface (Aurora, Vue 3)
	DEPENDS:= \
		+@LIGHTTPD_SSL \
		+lighttpd \
		+lighttpd-mod-cgi \
		+!LINUX_4_14:lighttpd-mod-openssl \
		+lighttpd-mod-redirect \
		+lighttpd-mod-setenv
endef

define Package/$(PKG_NAME)/config
	select PACKAGE_horizont
endef

define Package/$(PKG_NAME)/description
	WEB (Vue 3)
endef

define Build/Compile

ifeq ($(DONYX), 1)
	$(RM) $(PKG_BUILD_DIR)/src/css/*
	$(RM) $(PKG_BUILD_DIR)/src/assets/logo.svg
	$(RM) $(PKG_BUILD_DIR)/src/components/graphs/color.js
	$(RM) $(PKG_BUILD_DIR)/public/favicon*
	$(CP) $(PKG_BUILD_DIR)/donyx/src/* $(PKG_BUILD_DIR)/src/
	$(CP) $(PKG_BUILD_DIR)/donyx/public/favicon.png $(PKG_BUILD_DIR)/public/
	# donyx index.html (webpack) в Vite: корневой index.html с брендом donyx
	sed -e 's|/favicon.ico|/favicon.png|' -e 's|iRZ Control|Donyx - Control Panel|g' \
		$(PKG_BUILD_DIR)/index.html > $(PKG_BUILD_DIR)/index.html.tmp
	mv $(PKG_BUILD_DIR)/index.html.tmp $(PKG_BUILD_DIR)/index.html
endif
	# npm install, как прод-build.sh: package-lock.json не всегда в согласии с package.json
	cd $(PKG_BUILD_DIR) && npm install --no-audit --no-fund && npm run build
endef

define Package/$(PKG_NAME)/install
	$(CP) ./openwrt/* $(1)/
	$(INSTALL_DIR) $(1)/usr/share/aurora
	$(LN) -sf /usr/share/horizont/schema $(1)/usr/share/aurora/schema
	$(CP) $(PKG_BUILD_DIR)/dist/* $(1)/usr/share/aurora/

	$(INSTALL_DIR) $(1)/etc/ssl/
ifeq ($(DONYX), 1)
	$(CP) ./ssl/ssl-config-dnx $(1)/etc/ssl/https-tls.cnf
else
	$(CP) ./ssl/ssl-config-irz $(1)/etc/ssl/https-tls.cnf
endif

	$(INSTALL_DIR) $(1)/usr/share/aurora/script
	$(LN) -sf /usr/share/horizont/script/auth        $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/logout      $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/board       $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/dashboard   $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/dashboard.d $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/upload      $(1)/usr/share/aurora/script/
	$(LN) -sf /usr/share/horizont/script/wrapper     $(1)/usr/share/aurora/script/
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/lighttpd enable
/etc/init.d/lighttpd restart
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Веб-интерфейс Aurora (Vue 3 + Vite) для прод-прошивки (irzOS 1.2, horizont) —
# локальный вариант корпоративного aurora-фида (irzos-feeds/aurora): Vue 2 → Vue 3,
# webpack → Vite. Отличия от корпоративного: сборка — npm run build (dist/, уже с
# gzip-in-place через postbuild), icons.js — в репозитории (с import Iconify),
# пересобирать не нужно. Сборка из рабочей копии: AURORA_SRC=<каталог aurora> make …;
# иначе — последний коммит ветки vue3 (AURORA_PINNED — для сборки прошивки и fallback).
PKG_NAME:=aurora
# Вне сборки прошивки — версия выше продовой (0.1 dev / 1.2 release), чтобы opkg
# апгрейдил установленный aurora (Vue 2, 0.1-r11) на этот (Vue 3), а не считал даунгрейдом
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),1.3)
# номер выпуска: в сборке прошивки — calc_pkg_release; из рабочей копии (AURORA_SRC)
# или из последнего коммита ветки — время сборки UTC, иначе opkg не увидит пересобранный
# пакет как новый; из закреплённого коммита вне прошивки — 1
ifneq ($(AURORA_SRC)$(AURORA_LATEST),)
  ifeq ($(AURORA_RELEASE),)
    AURORA_RELEASE:=$(shell date -u +%y%m%d%H%M)
  endif
endif
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),$(or $(AURORA_RELEASE),1))

# Какой коммит:
#   AURORA_COMMIT=<хеш> make …   — этот;
#   сборка прошивки (FW_MAJOR)   — закреплённый AURORA_PINNED (воспроизводимость);
#   иначе                        — последний коммит ветки AURORA_BRANCH (vue3) на сервере
#                                  (git ls-remote при разборе Makefile). Нет доступа к
#                                  серверу — AURORA_PINNED с предупреждением.
# Локальный фид: каждая сборка из ветки получает номер выпуска по времени, поэтому
# opkg видит новую сборку (PKG_VERSION 1.3 вышепродовой 0.1 — установленный Vue 2
# обновляется, а не считается даунгрейдом).
PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@gitlab.radiofid.ru:Routers/Developing/zos/aurora.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
AURORA_PINNED:=0b714deaf14bd3d222e3ee64f858160ab732f1d3
AURORA_BRANCH?=vue3
ifeq ($(AURORA_COMMIT),)
  ifneq ($(FW_MAJOR)$(AURORA_SRC),)
    AURORA_COMMIT:=$(AURORA_PINNED)
  else
    AURORA_COMMIT:=$(shell git ls-remote $(PKG_SOURCE_URL) refs/heads/$(AURORA_BRANCH) 2>/dev/null | cut -f1)
    ifeq ($(AURORA_COMMIT),)
      $(warning aurora: no access to $(PKG_SOURCE_URL) ($(AURORA_BRANCH)), using the pinned commit $(AURORA_PINNED))
      AURORA_COMMIT:=$(AURORA_PINNED)
    else
      AURORA_LATEST:=1
    endif
  endif
endif
PKG_SOURCE_VERSION:=$(AURORA_COMMIT)
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

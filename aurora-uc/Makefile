include $(TOPDIR)/rules.mk
-include ../fw-version.mk

PKG_NAME:=aurora-uc
# в irzos-feeds версия и номер выпуска — как у остальных пакетов (fw-version.mk),
# вне его (локальный фид) — постоянные
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@github.com:artnavsegda/aurora.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=6ff8e0383f90dd088e739aae03539d69a5838f59
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

# отладка: собрать из рабочей копии вместо коммита — AURORA_UC_SRC=<каталог> make …
# (USE_SOURCE_DIR в командной строке подменил бы исходники и всем зависимостям)
ifneq ($(AURORA_UC_SRC),)
  USE_SOURCE_DIR:=$(AURORA_UC_SRC)
endif

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

# Аврора на протоколе horizon-uc (POST /script/wrapper {type, path, token, data}) вместо
# aurora: свой lighttpd (init, шаблон с корнем /usr/share/aurora-uc, TLS) — те же, что у
# aurora; схемы и варианты — horizon-uc, /system/access/web — тоже из horizon-uc
define Package/$(PKG_NAME)
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
	TITLE:=irzOS web interface (Aurora for horizon-uc)
	DEPENDS:= \
		+horizon-uc \
		+@LIGHTTPD_SSL \
		+lighttpd \
		+lighttpd-mod-cgi \
		+!LINUX_4_14:lighttpd-mod-openssl \
		+lighttpd-mod-redirect \
		+lighttpd-mod-setenv
	CONFLICTS:=aurora halo
endef

define Package/$(PKG_NAME)/description
	WEB (Vue) for horizon-uc, replaces aurora
endef

# icons.js (iconify) — в репозитории, пересобирать не нужно
define Build/Compile

ifeq ($(DONYX), 1)
	$(RM) $(PKG_BUILD_DIR)/src/css/*
	$(RM) $(PKG_BUILD_DIR)/src/assets/logo.svg
	$(RM) $(PKG_BUILD_DIR)/src/components/graphs/color.js
	$(RM) $(PKG_BUILD_DIR)/public/favicon*
	$(RM) $(PKG_BUILD_DIR)/public/index.html
	$(CP) $(PKG_BUILD_DIR)/donyx/src/* $(PKG_BUILD_DIR)/src/
	$(CP) $(PKG_BUILD_DIR)/donyx/public/* $(PKG_BUILD_DIR)/public/
endif
	# npm install, как прод-build.sh: package-lock.json Авроры не всегда в согласии с package.json
	cd $(PKG_BUILD_DIR) && npm install --no-audit --no-fund && npm run build
endef

define Package/$(PKG_NAME)/install
	$(CP) ./openwrt/* $(1)/
	$(INSTALL_DIR) $(1)/usr/share/aurora-uc
	$(CP) $(PKG_BUILD_DIR)/dist/* $(1)/usr/share/aurora-uc/
	$(LN) -sf /usr/share/horizon/schema $(1)/usr/share/aurora-uc/schema
	$(LN) -sf /usr/share/horizon/include $(1)/usr/share/aurora-uc/include

	$(INSTALL_DIR) $(1)/etc/ssl/
ifeq ($(DONYX), 1)
	$(CP) ./ssl/ssl-config-dnx $(1)/etc/ssl/https-tls.cnf
else
	$(CP) ./ssl/ssl-config-irz $(1)/etc/ssl/https-tls.cnf
endif

	# CGI horizon-uc по прод-путям (пакет horizon-uc)
	$(INSTALL_DIR) $(1)/usr/share/aurora-uc/script
	for f in wrapper auth logout dashboard dashboard.d upload; do \
		$(LN) -sf /usr/share/horizont/script/$$$$f $(1)/usr/share/aurora-uc/script/; \
	done
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/lighttpd enable
/etc/init.d/lighttpd restart
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

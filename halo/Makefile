include $(TOPDIR)/rules.mk
-include ../fw-version.mk

PKG_NAME:=halo
# в irzos-feeds версия и номер выпуска — как у остальных пакетов (fw-version.mk),
# вне его (локальный фид) — постоянные
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/artnavsegda/donyx.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=348a7e8470d6cd7ba53b947ad36b969bb0f9112f
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)/Default
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
endef

# замена aurora: свой lighttpd (init, шаблон с корнем /usr/share/halo, TLS) и схема
# /system/access/web — те же, что у aurora
define Package/$(PKG_NAME)
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS web interface (Halo)
	DEPENDS:= \
		+@LIGHTTPD_SSL \
		+lighttpd \
		+lighttpd-mod-cgi \
		+!LINUX_4_14:lighttpd-mod-openssl \
		+lighttpd-mod-redirect \
		+lighttpd-mod-setenv
	CONFLICTS:=aurora
endef

define Package/$(PKG_NAME)/config
	select PACKAGE_horizont
endef

define Package/$(PKG_NAME)/description
	WEB (Svelte), replaces aurora
endef

# рядом с aurora: /halo/ на её веб-сервере (корень /usr/share/aurora)
define Package/$(PKG_NAME)-preview
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS web interface (Halo), preview next to aurora
	DEPENDS:=+aurora
endef

define Package/$(PKG_NAME)-preview/description
	WEB (Svelte) at /halo/ alongside aurora
endef

# сборка Vite: сжатые *.js.gz/*.css.gz — под исходными именами (lighttpd отдаёт .js/.css
# с Content-Encoding: gzip, шаблон aurora), прочие сжатые — обратно; mockServiceWorker
# нужен только Storybook
define Halo/Build
	cd $(PKG_BUILD_DIR) && npx vite build --base $(2) --outDir $(1) --emptyOutDir
	rm -f $(1)/mockServiceWorker.js $(1)/mockServiceWorker.js.gz
	cd $(1) && for f in $$$$(find . -name '*.gz'); do \
		b=$$$${f%.gz}; \
		case "$$$$b" in *.js|*.css) mv "$$$$f" "$$$$b" ;; *) gunzip -f "$$$$f" ;; esac; \
	done
	$(if $(filter 1,$(DONYX)),$(SED) 's/data-theme="irz"/data-theme="donyx"/' $(1)/index.html)
endef

define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files,/)
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files-preview,/halo/)
endef

define Package/$(PKG_NAME)/install
	$(CP) ./openwrt/* $(1)/
	$(INSTALL_DIR) $(1)/usr/share/halo
	$(LN) -sf /usr/share/horizont/schema $(1)/usr/share/halo/schema
	$(CP) $(PKG_BUILD_DIR)/pkg-files/* $(1)/usr/share/halo/

	$(INSTALL_DIR) $(1)/etc/ssl/
ifeq ($(DONYX), 1)
	$(CP) ./ssl/ssl-config-dnx $(1)/etc/ssl/https-tls.cnf
else
	$(CP) ./ssl/ssl-config-irz $(1)/etc/ssl/https-tls.cnf
endif

	$(INSTALL_DIR) $(1)/usr/share/halo/script
	$(LN) -sf /usr/share/horizont/script/auth        $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/logout      $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/board       $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/dashboard   $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/dashboard.d $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/upload      $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/wrapper     $(1)/usr/share/halo/script/
endef

define Package/$(PKG_NAME)-preview/install
	$(INSTALL_DIR) $(1)/usr/share/aurora/halo
	$(CP) $(PKG_BUILD_DIR)/pkg-files-preview/* $(1)/usr/share/aurora/halo/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
$(eval $(call BuildPackage,$(PKG_NAME)-preview))

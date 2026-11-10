include $(TOPDIR)/rules.mk
-include ../fw-version.mk

PKG_NAME:=halo
# в irzos-feeds версия и номер выпуска — как у остальных пакетов (fw-version.mk),
# вне его (локальный фид) — постоянные
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git@github.com:artnavsegda/donyx.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=cbe5e5c2e0d6b350a70c7c9589cf57b0aabfebf0
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

# общий рантайм Halo и модулей (halo-mod-*): Svelte этой версии и набор @halo/ui в
# /usr/share/halo/runtime/. Модуль собран под точную версию Svelte и зависит от виртуального
# пакета halo-svelte-<версия>; версия — как в package.json donyx (проверяется при сборке)
HALO_SVELTE:=5.57.3

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
	PROVIDES:=halo-svelte-$(HALO_SVELTE)
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

# бренд выбирается при сборке (режим Vite): в сборку попадает только его оформление,
# check-brand.mjs проверяет, что от другого бренда ничего не осталось
HALO_BRAND:=$(if $(filter 1,$(DONYX)),donyx,irz)

# сборка Vite: сжатые *.js.gz/*.css.gz — под исходными именами (lighttpd отдаёт .js/.css
# с Content-Encoding: gzip, шаблон aurora), прочие сжатые — обратно
define Halo/Build
	cd $(PKG_BUILD_DIR) && npx vite build --mode $(HALO_BRAND) --base $(2) --outDir $(1) --emptyOutDir
	# рантайм: Halo импортирует Svelte из ./runtime/ (относительно своих assets/)
	cd $(PKG_BUILD_DIR) && npx vite build -c vite.runtime.config.ts --mode $(HALO_BRAND) --outDir $(1)/runtime --emptyOutDir
	# проверка бренда — только в исходнике с раздельной сборкой (ветка split donyx)
	cd $(PKG_BUILD_DIR) && if [ -f scripts/check-brand.mjs ]; then node scripts/check-brand.mjs $(HALO_BRAND) $(1); fi
	cd $(1) && for f in $$$$(find . -name '*.gz'); do \
		b=$$$${f%.gz}; \
		case "$$$$b" in *.js|*.css) mv "$$$$f" "$$$$b" ;; *) gunzip -f "$$$$f" ;; esac; \
	done
endef

define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	# версия Svelte в package.json должна совпадать с HALO_SVELTE (рантайм модулей)
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files,/)
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files-preview,/halo/)
endef

define Package/$(PKG_NAME)/install
	$(CP) ./openwrt/* $(1)/
	$(INSTALL_DIR) $(1)/usr/share/halo
	$(LN) -sf /usr/share/horizont/schema $(1)/usr/share/halo/schema
	$(CP) $(PKG_BUILD_DIR)/pkg-files/* $(1)/usr/share/halo/
	# модули (пакеты halo-mod-*) кладут сюда свои сборки, а CGI — в script/<имя>/;
	# модули сводки — в modules/dashboard/<label>/ (Halo ищет их по label раздела)
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard

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

# манифест модулей (modules/manifest.js, его подключает index.html) — по установленным модулям;
# при обновлении halo каталог modules/ остаётся, файл пересобирается
define Package/$(PKG_NAME)/postinst
#!/bin/sh
sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
exit 0
endef

define Package/$(PKG_NAME)-preview/install
	$(INSTALL_DIR) $(1)/usr/share/aurora/halo
	$(CP) $(PKG_BUILD_DIR)/pkg-files-preview/* $(1)/usr/share/aurora/halo/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
$(eval $(call BuildPackage,$(PKG_NAME)-preview))

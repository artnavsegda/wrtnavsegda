include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-gps»: раздел gps (скрипт 0910-gps.uc пакета gpsd, без изменений) —
# значения приёмника, карта (Leaflet, офлайн-суша world-atlas) и глобус (d3-geo). Свои
# библиотеки модуля — modules/dash-gps/package.json. Загрузка отложенная: сборка — в
# /usr/share/halo/modules/dashboard/gps/ без preload, карта с библиотеками — отдельным файлом.
# Зависит от пакета gpsd: без приёмника раздела gps нет.
PKG_NAME:=halo-mod-dash-gps
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

# исходник — тот же репозиторий, что у halo (modules/dash-gps), и тот же коммит: модуль
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
	TITLE:=Halo dashboard module: GPS map and globe
	DEPENDS:=+halo +$(if $(filter 1,$(DONYX)),dnxos-gpsd,irzos-gpsd)
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE)
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: GPS receiver values, map and globe
endef

# сжатые *.js/*.css — под исходными именами (lighttpd отдаёт их с Content-Encoding: gzip)
define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	cd $(PKG_BUILD_DIR)/modules/dash-gps && npm ci --no-audit --no-fund
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/dash-gps/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/dash-gps/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/gps
	$(CP) $(PKG_BUILD_DIR)/modules/dash-gps/dist/* $(1)/usr/share/halo/modules/dashboard/gps/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

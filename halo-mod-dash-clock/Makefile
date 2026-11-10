include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-clock»: часы роутера и время работы — пример модуля со своими
# данными (скрипт раздела clock в dashboard.d horizont) и отложенной загрузкой: сборка —
# в /usr/share/halo/modules/dashboard/clock/ без preload, Halo грузит её по label раздела,
# когда он пришёл. Пакет удалён — нет и раздела.
PKG_NAME:=halo-mod-dash-clock
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

# исходник — тот же репозиторий, что у halo (modules/dash-clock), и тот же коммит: модуль
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
	TITLE:=Halo dashboard module: clock and uptime
	DEPENDS:=+halo
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE)
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: router clock and uptime
endef

# сжатые *.js/*.css — под исходными именами (lighttpd отдаёт их с Content-Encoding: gzip)
define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/dash-clock/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/dash-clock/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/clock
	$(CP) $(PKG_BUILD_DIR)/modules/dash-clock/dist/* $(1)/usr/share/halo/modules/dashboard/clock/
	$(INSTALL_DIR) $(1)/usr/share/horizont/script/dashboard.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/dash-clock/backend/dashboard.d/0150-clock.uc $(1)/usr/share/horizont/script/dashboard.d/
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

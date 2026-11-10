include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-gauge»: раздел hardware (STORAGE, RAM, CPU) кольцами.
# Сборка — в /usr/share/halo/modules/dashboard/hardware/: Halo грузит модуль по label раздела
# сводки (/script/dashboard, бэкенд без изменений). Альтернатива — halo-mod-dash-hbar (полоски): данные те же, каталог
# тот же — пакеты конфликтуют, в сборку ставится один. Нет ни одного — обычные карточки.
PKG_NAME:=halo-mod-dash-gauge
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

# исходник — тот же репозиторий, что у halo (modules/dash-gauge), и тот же коммит: модуль
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
	TITLE:=Halo dashboard module: hardware gauges
	DEPENDS:=+halo
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE)
	CONFLICTS:=halo-mod-dash-hbar
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: STORAGE, RAM and CPU as ring gauges
endef

# сжатые *.js/*.css — под исходными именами (lighttpd отдаёт их с Content-Encoding: gzip)
define Build/Compile
	cd $(PKG_BUILD_DIR) && npm ci --no-audit --no-fund
	test "$$$$(node -p "require('$(PKG_BUILD_DIR)/node_modules/svelte/package.json').version")" = "$(HALO_SVELTE)"
	cd $(PKG_BUILD_DIR) && npx vite build -c modules/dash-gauge/vite.config.ts
	cd $(PKG_BUILD_DIR)/modules/dash-gauge/dist && for f in $$$$(find . -name '*.gz'); do \
		mv "$$$$f" "$$$${f%.gz}"; \
	done
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/hardware
	$(CP) $(PKG_BUILD_DIR)/modules/dash-gauge/dist/* $(1)/usr/share/halo/modules/dashboard/hardware/
	# лёгкий модуль: грузится сразу, вместе с основным бандлом (манифест halo-modules)
	touch $(1)/usr/share/halo/modules/dashboard/hardware/preload
endef

# манифест модулей Halo (предзагрузка): пересобрать по установленным модулям
define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -f "$${IPKG_INSTROOT}/usr/libexec/halo-modules" ] && sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
[ -f "$${IPKG_INSTROOT}/usr/libexec/halo-modules" ] && sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

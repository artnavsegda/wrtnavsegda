include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-gps»: раздел gps (0910-gps.uc пакета gpsd, без изменений) —
# значения приёмника, карта (Leaflet, офлайн-суша world-atlas) и глобус (d3-geo). Свои
# библиотеки — modules/dash-gps/package.json. Загрузка отложенная (без preload), карта с
# библиотеками — ещё и отдельным файлом. Зависит от пакета gpsd: без приёмника раздела нет.
PKG_NAME:=halo-mod-dash-gps

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: GPS map and globe
	DEPENDS:=+$(if $(filter 1,$(DONYX)),dnxos-gpsd,irzos-gpsd)
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: GPS receiver values, map and globe
endef

# условная точка карты без фиксации (нет координат) — штаб-квартира бренда сборки: iRZ —
# Санкт-Петербург, Donyx — Шэньчжэнь (маркер карты donyx.com/contact-us); "<широта>,<долгота>"
GPS_DEFAULT_IRZ ?= 59.9386,30.3141
GPS_DEFAULT_DNX ?= 22.5278,114.0765
export VITE_GPS_DEFAULT:=$(if $(filter 1,$(DONYX)),$(GPS_DEFAULT_DNX),$(GPS_DEFAULT_IRZ))

define Build/Compile
	$(call Halo/ModuleCompile,dash-gps)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/gps
	$(CP) $(PKG_BUILD_DIR)/modules/dash-gps/dist/* $(1)/usr/share/halo/modules/dashboard/gps/
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
$(call Halo/Modules)
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
$(call Halo/Modules)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

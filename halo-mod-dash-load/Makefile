include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-load»: график нагрузки — CPU, занятая память, load average за час и
# за сутки. Данные — служба метрик Halo (виртуальный halo-metrics-backend: halo-metrics или
# halo-metrics-collectd): описание метрики для обоих вариантов — metrics.d/load.uc и
# load.collectd.json, раздел load сводки (dashboard.d horizont) — последняя точка, история —
# CGI /script/metrics/history. Загрузка отложенная (без preload). Настройки — схема
# /system/dashboard-load (какие графики, шаг сбора, сколько истории; uci halo-metrics.load,
# применяет reload службы метрик).
PKG_NAME:=halo-mod-dash-load

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: load chart
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE), halo-runtime-$(HALO_RUNTIME), halo-metrics-backend
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: CPU, memory and load average chart (last hour and day)
endef

define Build/Compile
	$(call Halo/ModuleCompile,dash-load)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/load
	$(CP) $(PKG_BUILD_DIR)/modules/dash-load/dist/* $(1)/usr/share/halo/modules/dashboard/load/
	$(INSTALL_DIR) $(1)/usr/share/halo/metrics.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/dash-load/backend/metrics.d/* $(1)/usr/share/halo/metrics.d/
	$(INSTALL_DIR) $(1)/usr/share/horizont/script/dashboard.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/dash-load/backend/dashboard.d/0160-load.uc $(1)/usr/share/horizont/script/dashboard.d/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system $(1)/usr/share/horizont/script/subscript/halo $(1)/etc/uci-defaults
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/dash-load/backend/schema/system/dashboard-load.json $(1)/usr/share/horizont/schema/system/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/dash-load/backend/script/subscript/halo/dash-load.uc $(1)/usr/share/horizont/script/subscript/halo/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/dash-load/backend/uci-defaults/95_halo-dash-load $(1)/etc/uci-defaults/
endef

# halo-modules перечитывает и сборщики службы метрик (reload halo-metrics)
define Package/$(PKG_NAME)/postinst
#!/bin/sh
$(call Halo/Modules)
$(call Halo/ResetSchemas)
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
$(call Halo/Modules)
$(call Halo/ResetSchemas)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

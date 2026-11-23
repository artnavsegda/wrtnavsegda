include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-webgl»: текущая нагрузка (CPU, занятая память, load average) —
# WebGL-сцена с шейдером. Данные те же, что у halo-mod-dash-load: служба метрик Halo
# (metrics.d/load.uc и load.collectd.json), раздел load сводки — dashboard.d/0160-load.uc.
# Ставится вместо dash-load (общий label раздела load): пакеты конфликтуют. Сборка — в
# /usr/share/halo/modules/dashboard/load/, без preload (загрузка отложенная).
PKG_NAME:=halo-mod-dash-webgl

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: current load (WebGL)
	CONFLICTS:=halo-mod-dash-load
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE), halo-runtime-$(HALO_RUNTIME), halo-metrics-backend
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: CPU, memory and load average as a live WebGL shader scene
endef

define Build/Compile
	$(call Halo/ModuleCompile,dash-webgl)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/load
	$(CP) $(PKG_BUILD_DIR)/modules/dash-webgl/dist/* $(1)/usr/share/halo/modules/dashboard/load/
	# бэкенд метрики и раздел сводки — те же, что у dash-load
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

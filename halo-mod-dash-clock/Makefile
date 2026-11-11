include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-clock»: часы роутера и время работы — пример модуля со своими
# данными (раздел clock: скрипт dashboard.d horizont) и отложенной загрузкой: сборка — в
# /usr/share/halo/modules/dashboard/clock/ без preload. Пакет удалён — нет и раздела.
PKG_NAME:=halo-mod-dash-clock

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: clock and uptime
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: router clock and uptime
endef

define Build/Compile
	$(call Halo/ModuleCompile,dash-clock)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/clock
	$(CP) $(PKG_BUILD_DIR)/modules/dash-clock/dist/* $(1)/usr/share/halo/modules/dashboard/clock/
	$(INSTALL_DIR) $(1)/usr/share/horizont/script/dashboard.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/dash-clock/backend/dashboard.d/0150-clock.uc $(1)/usr/share/horizont/script/dashboard.d/
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

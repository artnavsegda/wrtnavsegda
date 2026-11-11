include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-gauge»: раздел hardware (STORAGE, RAM, CPU) кольцами. Сборка — в
# /usr/share/halo/modules/dashboard/hardware/ (Halo грузит её по label раздела, сразу —
# preload). Альтернатива — halo-mod-dash-hbar (полоски): данные те же (0100-hardware.uc
# horizont), каталог тот же — пакеты конфликтуют, ставится один. Нет ни одного — карточки.
PKG_NAME:=halo-mod-dash-gauge

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: hardware gauges
	CONFLICTS:=halo-mod-dash-hbar
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: STORAGE, RAM and CPU as ring gauges
endef

define Build/Compile
	$(call Halo/ModuleCompile,dash-gauge)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/hardware
	$(CP) $(PKG_BUILD_DIR)/modules/dash-gauge/dist/* $(1)/usr/share/halo/modules/dashboard/hardware/
	# лёгкий модуль: грузится сразу, вместе с основным бандлом (манифест halo-modules)
	touch $(1)/usr/share/halo/modules/dashboard/hardware/preload
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

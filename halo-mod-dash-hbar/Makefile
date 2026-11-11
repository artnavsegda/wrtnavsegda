include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль сводки Halo «dash-hbar»: раздел hardware (STORAGE, RAM, CPU) полосками. Сборка — в
# /usr/share/halo/modules/dashboard/hardware/ (Halo грузит её по label раздела, сразу —
# preload). Альтернатива — halo-mod-dash-gauge (кольца): данные те же (0100-hardware.uc
# horizont), каталог тот же — ставится один (CONFLICTS — у dash-gauge: взаимный — рекурсия
# kconfig; обратно opkg не даст поставить из-за общих файлов). Нет ни одного — карточки.
PKG_NAME:=halo-mod-dash-hbar

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo dashboard module: hardware bars
endef

define Package/$(PKG_NAME)/description
	Halo dashboard: STORAGE, RAM and CPU as horizontal bars
endef

define Build/Compile
	$(call Halo/ModuleCompile,dash-hbar)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/hardware
	$(CP) $(PKG_BUILD_DIR)/modules/dash-hbar/dist/* $(1)/usr/share/halo/modules/dashboard/hardware/
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

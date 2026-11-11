include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Схема-модуль Halo «firmware»: обновление встроенного ПО — инструкция, ссылка на свежие
# прошивки на сайте (по бренду сборки), загрузка образа и запуск обновления (действие upgrade
# /system/management, своего бэкенда нет). Схема /system/firmware ("$module").
PKG_NAME:=halo-mod-firmware

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

# страница свежих прошивок на сайте — по бренду сборки (как ssl-конфиг пакета halo)
FIRMWARE_URL_IRZ ?= https://faq.irz.net/
FIRMWARE_URL_DNX ?= https://donyx.com/
FIRMWARE_URL:=$(if $(filter 1,$(DONYX)),$(FIRMWARE_URL_DNX),$(FIRMWARE_URL_IRZ))

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo module: firmware upgrade
endef

define Package/$(PKG_NAME)/description
	Halo page System / Firmware: upgrade instructions, link to the latest firmware, upload and upgrade
endef

define Build/Compile
	$(call Halo/ModuleCompile,firmware)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/firmware
	$(CP) $(PKG_BUILD_DIR)/modules/firmware/dist/* $(1)/usr/share/halo/modules/firmware/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system
	sed 's|@FIRMWARE_URL@|$(FIRMWARE_URL)|' $(PKG_BUILD_DIR)/modules/firmware/schema/system/firmware.json \
		> $(1)/usr/share/horizont/schema/system/firmware.json
endef

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

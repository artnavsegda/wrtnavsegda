include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Схема-модуль Halo «software» (как Software в LuCI): обновления установленных пакетов из фидов
# (с подтверждением списка), установка из фидов по имени с поиском, обновление списков (opkg
# update), загрузка своих ipk, удаление; сами репозитории — схема /system/repository пакета
# opkg-repository (на странице — ссылка на неё); схема /system/software ("$module"), сборка
# модуля и CGI его API (/script/software/…, ucode).
PKG_NAME:=halo-mod-software

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo module: software packages
endef

define Package/$(PKG_NAME)/description
	Halo page System / Software: updates, install from repositories with search,
	package lists update, upload of own packages, installed packages and removal
endef

define Build/Compile
	$(call Halo/ModuleCompile,software)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/software
	$(CP) $(PKG_BUILD_DIR)/modules/software/dist/* $(1)/usr/share/halo/modules/software/
	$(INSTALL_DIR) $(1)/usr/share/halo/script/software
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/software/backend/script/software/* $(1)/usr/share/halo/script/software/
	$(INSTALL_DIR) $(1)/usr/share/ucode/halo
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/software/backend/ucode/halo/software.uc $(1)/usr/share/ucode/halo/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/software/schema/system/software.json $(1)/usr/share/horizont/schema/system/
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

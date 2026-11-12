include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Схема-модуль Halo «firmware»: обновление встроенного ПО — каталог сборок (прототип внешнего
# API: манифест buildbot через lighttpd mod_proxy /halo-firmware/buildbot/, его и образ
# скачивает браузер), сверка с последней сборкой канала и обновление до неё, ручная загрузка
# образа, ссылка на сайт (по бренду сборки), действие upgrade /system/management. CGI
# /script/firmware/info — плата, бренд и версия. Схема /system/firmware ("$module").
PKG_NAME:=halo-mod-firmware

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

# страница свежих прошивок на сайте — по бренду сборки (как ssl-конфиг пакета halo)
FIRMWARE_URL_IRZ ?= https://faq.irz.net/
FIRMWARE_URL_DNX ?= https://donyx.com/
FIRMWARE_URL:=$(if $(filter 1,$(DONYX)),$(FIRMWARE_URL_DNX),$(FIRMWARE_URL_IRZ))
# бренд сборки в каталоге buildbot (если CGI не отвечает — имя образа по бренду из схемы)
FIRMWARE_BRAND:=$(if $(filter 1,$(DONYX)),dnxOS,irzOS)

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo module: firmware upgrade
	DEPENDS+=+lighttpd-mod-proxy
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
	sed -e 's|@FIRMWARE_URL@|$(FIRMWARE_URL)|' -e 's|@BRAND@|$(FIRMWARE_BRAND)|' \
		$(PKG_BUILD_DIR)/modules/firmware/schema/system/firmware.json \
		> $(1)/usr/share/horizont/schema/system/firmware.json
	$(INSTALL_DIR) $(1)/usr/share/halo/script/firmware $(1)/usr/share/halo/lighttpd
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/firmware/backend/script/firmware/* $(1)/usr/share/halo/script/firmware/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/firmware/backend/lighttpd/50-halo-firmware.conf $(1)/usr/share/halo/lighttpd/
endef

# прокси каталога — в конфиг lighttpd, только если есть mod_proxy: без модуля lighttpd с этим
# конфигом не запускается и пропадает весь веб (так было на R50). Без прокси модуль работает,
# каталог buildbot — нет (ручная загрузка образа остаётся)
define Firmware/ProxyConf
[ -n "$${IPKG_INSTROOT}" ] || {
	if [ -f /usr/lib/lighttpd/mod_proxy.so ]; then
		ln -sf /usr/share/halo/lighttpd/50-halo-firmware.conf /etc/lighttpd/halo.d/50-halo-firmware.conf
	else
		rm -f /etc/lighttpd/halo.d/50-halo-firmware.conf
		echo "halo-mod-firmware: no lighttpd mod_proxy, the firmware catalog is disabled" >&2
	fi
}
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
$(call Firmware/ProxyConf)
$(call Halo/Modules)
$(call Halo/ResetSchemas)
$(call Halo/RestartWeb)
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || rm -f /etc/lighttpd/halo.d/50-halo-firmware.conf
$(call Halo/Modules)
$(call Halo/ResetSchemas)
$(call Halo/RestartWeb)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

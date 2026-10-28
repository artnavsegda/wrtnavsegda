include $(TOPDIR)/rules.mk
-include ../fw-version.mk

PKG_NAME:=horizon-uc
# в irzos-feeds версия и номер выпуска — как у остальных пакетов (fw-version.mk),
# вне его (локальный фид) — постоянные
PKG_VERSION:=$(if $(FW_MAJOR),$(FW_MAJOR).$(FW_MINOR),0.1)
PKG_RELEASE:=$(if $(FW_MAJOR),$(call calc_pkg_release,$(CURDIR),OSS),1)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=https://github.com/artnavsegda/horizon-uc.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=1fecbdf8ff8b690490b6d81211fc2e11183362f8
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz
PKG_MIRROR_HASH:=skip

PKG_MAINTAINER:=iRZ Electronics <irz.net>

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)/Default
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
endef

# замена horizont: демон на ucode, схемы и скрипты в /usr/share/horizon; по прод-путям
# /usr/share/horizont — то, что ищут веб-интерфейсы (script/: aurora, halo) и пакеты iRZ
# (lib/, модуль horizont.utils, dashboard.d)
define Package/$(PKG_NAME)
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS backend service and scripts (ucode)
	DEPENDS:= \
		+ucode \
		+ucode-mod-fs \
		+ucode-mod-math \
		+ucode-mod-socket \
		+ucode-mod-struct \
		+ucode-mod-ubus \
		+ucode-mod-uci \
		+ucode-mod-uloop \
		+ucode-mod-inotify \
		+ucode-mod-pam \
		+rpcd
	CONFLICTS:=horizont
endef

define Package/$(PKG_NAME)/description
	Backend (ucode), replaces horizont
endef

define Package/zenith-uc
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS cli interface (ucode)
	DEPENDS:=+$(PKG_NAME) +ucode-mod-readline
	CONFLICTS:=zenith
endef

define Package/zenith-uc/description
	CLI (ucode), replaces zenith
endef

# всё на ucode — собирать нечего
define Build/Compile
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/horizon
	$(CP) $(PKG_BUILD_DIR)/horizon $(PKG_BUILD_DIR)/utils $(1)/usr/share/horizon/
	$(CP) $(PKG_BUILD_DIR)/schema $(PKG_BUILD_DIR)/include $(PKG_BUILD_DIR)/script $(1)/usr/share/horizon/
	$(CP) $(PKG_BUILD_DIR)/test/langs $(1)/usr/share/horizon/
	# мок — только стенд: на устройстве отсутствующий скрипт остаётся ошибкой
	$(RM) $(1)/usr/share/horizon/script/mock.uc

	# CGI веб-интерфейсов: lighttpd выполняет /script/* по #!
	$(INSTALL_DIR) $(1)/usr/share/horizont/script/dashboard.d
	for f in wrapper auth logout dashboard upload; do \
		$(INSTALL_BIN) $(PKG_BUILD_DIR)/www/$$$$f.uc $(1)/usr/share/horizont/script/$$$$f; \
	done
	$(CP) $(PKG_BUILD_DIR)/www/dashboard.d/* $(1)/usr/share/horizont/script/dashboard.d/

	# из прод-horizont: их подключают скрипты и хуки пакетов iRZ
	$(INSTALL_DIR) $(1)/usr/share/horizont/lib $(1)/usr/share/ucode/horizont
	$(CP) $(PKG_BUILD_DIR)/files/usr/share/horizont/lib/envs.sh \
		$(PKG_BUILD_DIR)/files/usr/share/horizont/lib/function.sh \
		$(PKG_BUILD_DIR)/files/usr/share/horizont/lib/netifd-proto.uc \
		$(1)/usr/share/horizont/lib/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/files/usr/share/ucode/horizont/utils.uc $(1)/usr/share/ucode/horizont/

	$(INSTALL_DIR) $(1)/etc/init.d $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/files/etc/init.d/horizon $(1)/etc/init.d/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/files/etc/init.d/horizont $(1)/etc/init.d/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/files/usr/bin/hostname $(1)/usr/bin/
	# процесс демона называется horizont: хуки iRZ проверяют `pidof horizont`
	$(LN) ucode $(1)/usr/bin/horizont
endef

define Package/zenith-uc/install
	$(INSTALL_DIR) $(1)/usr/share/horizon $(1)/usr/bin
	$(CP) $(PKG_BUILD_DIR)/zenith $(1)/usr/share/horizon/
	$(RM) $(1)/usr/share/horizon/zenith/test.uc
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/files/usr/bin/zenith $(1)/usr/bin/
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/horizon enable
/etc/init.d/horizon restart
exit 0
endef

define Package/$(PKG_NAME)/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/horizon stop
/etc/init.d/horizon disable
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
$(eval $(call BuildPackage,zenith-uc))

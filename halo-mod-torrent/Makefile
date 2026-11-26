include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль Halo «torrent»: схема /service/torrent, сборка модуля и CGI /script/torrent/api —
# прокси к transmission-daemon (RPC только на 127.0.0.1:9091). Ставится на любой вариант
# Halo (halo, halo-preview); transmission-daemon тянется зависимостью.
PKG_NAME:=halo-mod-torrent

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	DEPENDS:=+transmission-daemon
	TITLE:=Halo module: torrent
endef

define Package/$(PKG_NAME)/description
	Halo page Service / Torrents: Transmission list, speeds, storage, files, peers,
	trackers, add magnet/URL/.torrent and start/stop/verify/remove actions.
endef

define Build/Compile
	$(call Halo/ModuleCompile,torrent)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/torrent
	$(CP) $(PKG_BUILD_DIR)/modules/torrent/dist/* $(1)/usr/share/halo/modules/torrent/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/service
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/torrent/schema/service/torrent.json $(1)/usr/share/horizont/schema/service/
	$(INSTALL_DIR) $(1)/usr/share/halo/script/torrent
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/torrent/backend/script/torrent/* $(1)/usr/share/halo/script/torrent/
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

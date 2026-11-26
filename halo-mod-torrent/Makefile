include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Модуль Halo «torrent» — две роли в одном пакете:
#   страница  — схема /service/torrent, сборка modules/torrent и CGI /script/torrent/api
#               (прокси к transmission-daemon, RPC только на 127.0.0.1:9091);
#   сводка    — карточка дашборда: сборка modules/dash-torrent (label раздела "torrent"),
#               раздел — dashboard.d/0120-torrent.uc, история скоростей — метрика
#               metrics.d/torrent.uc службы halo-metrics (CGI /script/metrics/history).
# Ставится на любой вариант Halo (halo, halo-preview); transmission-daemon и служба метрик
# тянутся зависимостями.
PKG_NAME:=halo-mod-torrent

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo module: torrent (page and dashboard card)
	EXTRA_DEPENDS:=halo-svelte-$(HALO_SVELTE), halo-runtime-$(HALO_RUNTIME), halo-metrics-backend
	DEPENDS:=+transmission-daemon
endef

define Package/$(PKG_NAME)/description
	Halo page Service / Torrents: Transmission list, speeds, storage, files, peers,
	trackers, add magnet/URL/.torrent and start/stop/verify/remove actions.
	Dashboard card: speeds, last-hour sparkline, counters and active torrents.
endef

define Build/Compile
	$(call Halo/ModuleCompile,torrent)
	$(call Halo/ModuleCompile,dash-torrent)
endef

define Package/$(PKG_NAME)/install
	# страница
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/torrent
	$(CP) $(PKG_BUILD_DIR)/modules/torrent/dist/* $(1)/usr/share/halo/modules/torrent/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/service
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/torrent/schema/service/torrent.json $(1)/usr/share/horizont/schema/service/
	$(INSTALL_DIR) $(1)/usr/share/halo/script/torrent
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/torrent/backend/script/torrent/* $(1)/usr/share/halo/script/torrent/
	# карточка дашборда
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard/torrent
	$(CP) $(PKG_BUILD_DIR)/modules/dash-torrent/dist/* $(1)/usr/share/halo/modules/dashboard/torrent/
	$(INSTALL_DIR) $(1)/usr/share/horizont/script/dashboard.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/torrent/backend/dashboard.d/0120-torrent.uc $(1)/usr/share/horizont/script/dashboard.d/
	# история скоростей для спарклайна
	$(INSTALL_DIR) $(1)/usr/share/halo/metrics.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/torrent/backend/metrics.d/torrent.uc $(1)/usr/share/halo/metrics.d/
	# общий RPC-клиент (сборщик метрики и раздел сводки)
	$(INSTALL_DIR) $(1)/usr/share/ucode/torrent
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/torrent/backend/lib/torrent/rpc.uc $(1)/usr/share/ucode/torrent/
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

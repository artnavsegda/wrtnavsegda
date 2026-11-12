include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Фоновые метрики Halo: служба, которая собирает данные модулей непрерывно и хранит историю
# (кольца: час и сутки), и выдача — библиотека halo.metrics для CGI и разделов сводки, CGI
# /script/metrics/history. Два взаимозаменяемых варианта с одним API (виртуальный пакет
# halo-metrics-backend, модули зависят от него) — переключение заменой пакета:
#   halo-metrics           — своя служба на ucode (по умолчанию: без новых пакетов прошивки);
#   halo-metrics-collectd  — collectd с RRD (готовые плагины; ≈270 КБ флеша).
# Модуль приносит описание метрики для обоих: metrics.d/<имя>.uc и <имя>.collectd.json.
# Источник — donyx backend/metrics/.
PKG_NAME:=halo-metrics

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/halo-metrics/Default
	SECTION:=web
	CATEGORY:=Web Servers/Proxies
	SUBMENU:=Halo
	PKGARCH:=all
	PROVIDES:=halo-metrics-backend
endef

define Package/halo-metrics
$(call Package/halo-metrics/Default)
	TITLE:=Halo background metrics (ucode service)
	DEPENDS:=+ucode +ucode-mod-fs +ucode-mod-uloop +ucode-mod-ubus
endef

define Package/halo-metrics/description
	Background metrics for Halo modules: own ucode service with ring history in RAM
endef

define Package/halo-metrics-collectd
$(call Package/halo-metrics/Default)
	TITLE:=Halo background metrics (collectd + RRD)
	DEPENDS:=+ucode +ucode-mod-fs +collectd +collectd-mod-rrdtool +rrdtool1 \
		+collectd-mod-cpu +collectd-mod-memory +collectd-mod-load +collectd-mod-interface
	CONFLICTS:=halo-metrics
endef

define Package/halo-metrics-collectd/description
	Background metrics for Halo modules over collectd with RRD in RAM (same API as halo-metrics)
endef

define Build/Compile
endef

M:=$(PKG_BUILD_DIR)/backend/metrics

define Halo/MetricsCommon
	$(INSTALL_DIR) $(1)/usr/share/halo/metrics.d $(1)/usr/share/halo/script/metrics $(1)/usr/share/ucode/halo $(1)/etc/init.d $(1)/usr/libexec
	$(INSTALL_BIN) $(M)/common/history $(1)/usr/share/halo/script/metrics/
endef

define Package/halo-metrics/install
	$(call Halo/MetricsCommon,$(1))
	$(INSTALL_BIN) $(M)/own/halo-metrics $(1)/usr/libexec/
	$(INSTALL_BIN) $(M)/own/init.d-halo-metrics $(1)/etc/init.d/halo-metrics
	$(INSTALL_DATA) $(M)/own/metrics.uc $(1)/usr/share/ucode/halo/
endef

define Package/halo-metrics-collectd/install
	$(call Halo/MetricsCommon,$(1))
	$(INSTALL_BIN) $(M)/collectd/halo-metrics-collectd-conf $(1)/usr/libexec/
	$(INSTALL_BIN) $(M)/collectd/init.d-halo-metrics $(1)/etc/init.d/halo-metrics
	$(INSTALL_DATA) $(M)/collectd/metrics.uc $(1)/usr/share/ucode/halo/
endef

# CGI — ссылкой к aurora у halo-preview (halo-modules); служба — включить и запустить
define Package/halo-metrics/postinst
#!/bin/sh
$(call Halo/Modules)
[ -n "$${IPKG_INSTROOT}" ] || { /etc/init.d/halo-metrics enable; /etc/init.d/halo-metrics restart; }
exit 0
endef

define Package/halo-metrics-collectd/postinst
#!/bin/sh
$(call Halo/Modules)
# штатная служба collectd пакета не нужна: collectd запускает halo-metrics со своим конфигом
[ -n "$${IPKG_INSTROOT}" ] || {
	/etc/init.d/collectd disable 2>/dev/null; /etc/init.d/collectd stop 2>/dev/null
	/etc/init.d/halo-metrics enable; /etc/init.d/halo-metrics restart
}
exit 0
endef

define Package/halo-metrics/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || { /etc/init.d/halo-metrics stop; /etc/init.d/halo-metrics disable; }
exit 0
endef
Package/halo-metrics-collectd/prerm=$(Package/halo-metrics/prerm)

define Package/halo-metrics/postrm
#!/bin/sh
$(call Halo/Modules)
exit 0
endef
Package/halo-metrics-collectd/postrm=$(Package/halo-metrics/postrm)

$(eval $(call BuildPackage,halo-metrics))
$(eval $(call BuildPackage,halo-metrics-collectd))

include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Схема-модуль Halo «console»: SSH-консоль роутера в браузере. Клиент — xterm.js (свои
# библиотеки модуля, modules/console/package.json), на роутере — ttyd только на lo:7682 за
# lighttpd (WebSocket /halo-console/ws, mod_proxy, /etc/lighttpd/halo.d), в сеансе — ssh на
# этот же роутер: вход, права и ip-lock — как у обычного ssh. Схема /system/console.
# ttyd тянет libwebsockets-full: с libwebsockets-openssl (mosquitto) у них общие файлы.
PKG_NAME:=halo-mod-console

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
$(call Halo/ModuleDefault)
	TITLE:=Halo module: SSH console
	DEPENDS:=+ttyd +lighttpd-mod-proxy +openssh-client
endef

define Package/$(PKG_NAME)/description
	Halo page System / Console: SSH console of the router (xterm.js, ttyd)
endef

define Build/Compile
	$(call Halo/ModuleCompile,console)
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/console
	$(CP) $(PKG_BUILD_DIR)/modules/console/dist/* $(1)/usr/share/halo/modules/console/
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/console/schema/system/console.json $(1)/usr/share/horizont/schema/system/
	$(INSTALL_DIR) $(1)/usr/libexec $(1)/etc/init.d $(1)/etc/lighttpd/halo.d
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/console/backend/libexec/halo-console $(1)/usr/libexec/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/modules/console/backend/init.d/halo-console $(1)/etc/init.d/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/modules/console/backend/lighttpd/50-halo-console.conf $(1)/etc/lighttpd/halo.d/
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
$(call Halo/Modules)
$(call Halo/ResetSchemas)
[ -n "$${IPKG_INSTROOT}" ] && exit 0
# штатная служба пакета ttyd — вход /bin/login на всех адресах (7681): выключить, консоль —
# только своя, на lo (7682) за lighttpd
[ -x /etc/init.d/ttyd ] && { /etc/init.d/ttyd stop 2>/dev/null; /etc/init.d/ttyd disable; }
/etc/init.d/halo-console enable
/etc/init.d/halo-console restart 2>/dev/null
$(call Halo/RestartWeb)
exit 0
endef

define Package/$(PKG_NAME)/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/halo-console stop 2>/dev/null
/etc/init.d/halo-console disable
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
$(call Halo/Modules)
$(call Halo/ResetSchemas)
$(call Halo/RestartWeb)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

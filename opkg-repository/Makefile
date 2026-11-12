include $(TOPDIR)/rules.mk

# Репозитории пакетов (opkg feeds) в веб-интерфейсе и CLI: прод-схема horizont
# /system/repository со скриптом — список строк src/gz и src файлов /etc/opkg/*.conf, добавление
# (в customfeeds.conf, по желанию сразу с opkg update), изменение (адрес, сжатие, выключение —
# комментарием), удаление; действие update — opkg update с выводом потоком. Работает в Авроре,
# Halo и zenith (прод-horizont); пригодится halo-mod-software (новые пакеты — из репозиториев).
# Исходный код — в этом каталоге (files/).
PKG_NAME:=opkg-repository
PKG_VERSION:=0.1
PKG_RELEASE:=3
PKG_MAINTAINER:=iRZ Electronics <irz.net>
PKG_LICENSE:=MIT

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
	SECTION:=utils
	CATEGORY:=Utilities
	TITLE:=Package repositories (opkg feeds) schema for horizont
	PKGARCH:=all
	DEPENDS:=+ucode +ucode-mod-fs
endef

define Package/$(PKG_NAME)/description
	horizont schema /system/repository: list, add, edit and delete opkg feeds (/etc/opkg/*.conf)
	and run opkg update, for the web interface (Aurora, Halo) and the CLI (zenith)
endef

define Build/Compile
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/usr/share/horizont/schema/system $(1)/usr/share/horizont/script/subscript/system
	$(INSTALL_DATA) ./files/usr/share/horizont/schema/system/repository.json $(1)/usr/share/horizont/schema/system/
	$(INSTALL_BIN) ./files/usr/share/horizont/script/subscript/system/repository.uc $(1)/usr/share/horizont/script/subscript/system/
endef

# новая схема — в дерево horizont (запрос @reset внутреннего протокола, 127.0.0.1:65500)
define Horizont/ResetSchemas
[ -n "$${IPKG_INSTROOT}" ] || ucode -e 'import * as socket from "socket"; import {pack} from "struct"; let s = socket.connect("127.0.0.1", 65500, {family: socket.AF_INET, socktype: socket.SOCK_STREAM}); if (s) { let r = sprintf("%J", {type: "@reset", path: "/", user: "root", data: {}}); s.setopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, {sec: 10, usec: 0}); s.send(pack("<L", length(r)) + r); s.recv(4); s.close(); }' 2>/dev/null
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
$(call Horizont/ResetSchemas)
exit 0
endef

define Package/$(PKG_NAME)/postrm
#!/bin/sh
$(call Horizont/ResetSchemas)
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))

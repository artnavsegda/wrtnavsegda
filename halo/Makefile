include $(TOPDIR)/rules.mk
-include ../fw-version.mk

# Веб-интерфейс Halo для прод-прошивки (irzOS 1.2, horizont) — два варианта:
#   halo         — замена aurora: свой lighttpd (init, шаблон с корнем /usr/share/halo, TLS)
#                  и схема /system/access/web — те же файлы, что у aurora (CONFLICTS aurora:
#                  сначала opkg remove aurora);
#   halo-preview — рядом с aurora: /halo/ на её веб-сервере (корень /usr/share/aurora).
# Модули (halo-mod-*) ставятся на любой: сборки модулей — в /usr/share/halo/modules (у preview
# на него ссылается /usr/share/aurora/halo/modules), CGI — в /usr/share/halo/script/<имя> (у
# preview ссылки в /usr/share/aurora/script ставит halo-modules), настройки веб-сервера —
# /etc/lighttpd/halo.d/*.conf (подключает шаблон halo, у preview — строка в шаблоне aurora).
PKG_NAME:=halo

include ../halo.mk
include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)/Default
	SECTION:=custom
	CATEGORY:=irzOS
	PKGARCH:=all
	# рантайм модулей: Svelte этой версии и @halo/ui в <корень Halo>/runtime/
	PROVIDES:=halo-svelte-$(HALO_SVELTE)
endef

define Package/$(PKG_NAME)
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS web interface (Halo)
	DEPENDS:= \
		+@LIGHTTPD_SSL \
		+lighttpd \
		+lighttpd-mod-cgi \
		+!LINUX_4_14:lighttpd-mod-openssl \
		+lighttpd-mod-redirect \
		+lighttpd-mod-setenv
	CONFLICTS:=aurora halo-preview
endef

define Package/$(PKG_NAME)/config
	select PACKAGE_horizont
endef

define Package/$(PKG_NAME)/description
	WEB (Svelte), replaces aurora
endef

define Package/$(PKG_NAME)-preview
$(call Package/$(PKG_NAME)/Default)
	TITLE:=irzOS web interface (Halo), preview next to aurora
	DEPENDS:=+aurora
endef

define Package/$(PKG_NAME)-preview/description
	WEB (Svelte) at /halo/ alongside aurora
endef

# бренд выбирается при сборке (режим Vite): в сборку попадает только его оформление,
# check-brand.mjs проверяет, что от другого бренда ничего не осталось
HALO_BRAND:=$(if $(filter 1,$(DONYX)),donyx,irz)

# сборка Vite: сжатые *.js.gz/*.css.gz — под исходными именами (lighttpd отдаёт .js/.css
# с Content-Encoding: gzip, шаблон aurora), прочие сжатые — обратно
define Halo/Build
	cd $(PKG_BUILD_DIR) && npx vite build --mode $(HALO_BRAND) --base $(2) --outDir $(1) --emptyOutDir
	# рантайм: Halo импортирует Svelte из ./runtime/ (относительно своих assets/)
	cd $(PKG_BUILD_DIR) && npx vite build -c vite.runtime.config.ts --mode $(HALO_BRAND) --outDir $(1)/runtime --emptyOutDir
	# проверка бренда — только в исходнике с раздельной сборкой (ветка split donyx)
	cd $(PKG_BUILD_DIR) && if [ -f scripts/check-brand.mjs ]; then node scripts/check-brand.mjs $(HALO_BRAND) $(1); fi
	cd $(1) && for f in $$$$(find . -name '*.gz'); do \
		b=$$$${f%.gz}; \
		case "$$$$b" in *.js|*.css) mv "$$$$f" "$$$$b" ;; *) gunzip -f "$$$$f" ;; esac; \
	done
	# файлы меньше порога сжатия Vite (1 КБ: svelte.js рантайма и т. п.) остались несжатыми,
	# а lighttpd отдаёт все .js/.css с Content-Encoding: gzip — сжать и их
	cd $(1) && for f in $$$$(find . -name '*.js' -o -name '*.css'); do \
		gzip -t "$$$$f" 2>/dev/null || { gzip -9 -n -c "$$$$f" > "$$$$f.tmp" && mv "$$$$f.tmp" "$$$$f"; }; \
	done
endef

define Build/Compile
	$(call Halo/Npm)
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files,/)
	$(call Halo/Build,$(PKG_BUILD_DIR)/pkg-files-preview,/halo/)
endef

# общее обоих вариантов: каталоги модулей, утилита манифеста, настройки веб-сервера модулей
define Halo/InstallCommon
	$(INSTALL_DIR) $(1)/usr/share/halo/modules/dashboard $(1)/usr/share/halo/script
	$(INSTALL_DIR) $(1)/usr/libexec
	$(INSTALL_BIN) ./openwrt/usr/libexec/halo-modules $(1)/usr/libexec/
	$(INSTALL_DIR) $(1)/etc/lighttpd/halo.d
	$(INSTALL_DATA) ./files/halo.d/00-halo.conf $(1)/etc/lighttpd/halo.d/
endef

define Package/$(PKG_NAME)/install
	$(CP) ./openwrt/* $(1)/
	$(INSTALL_DIR) $(1)/usr/share/halo
	$(LN) -sf /usr/share/horizont/schema $(1)/usr/share/halo/schema
	$(CP) $(PKG_BUILD_DIR)/pkg-files/* $(1)/usr/share/halo/
	$(call Halo/InstallCommon,$(1))

	$(INSTALL_DIR) $(1)/etc/ssl/
ifeq ($(DONYX), 1)
	$(CP) ./ssl/ssl-config-dnx $(1)/etc/ssl/https-tls.cnf
else
	$(CP) ./ssl/ssl-config-irz $(1)/etc/ssl/https-tls.cnf
endif

	$(LN) -sf /usr/share/horizont/script/auth        $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/logout      $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/board       $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/dashboard   $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/dashboard.d $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/upload      $(1)/usr/share/halo/script/
	$(LN) -sf /usr/share/horizont/script/wrapper     $(1)/usr/share/halo/script/
endef

# манифест модулей (modules/manifest.js, его подключает index.html) — по установленным модулям;
# веб-сервер — на шаблоне halo (замена aurora: при её удалении lighttpd остановлен и выключен)
define Package/$(PKG_NAME)/postinst
#!/bin/sh
sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/lighttpd enable
/etc/init.d/lighttpd restart
exit 0
endef

# opkg не удаляет ссылки на каталоги (schema, script/dashboard.d) и не знает о манифесте — убрать
define Package/$(PKG_NAME)/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
rm -f /usr/share/halo/schema /usr/share/halo/script/dashboard.d /usr/share/halo/modules/manifest.js
exit 0
endef

# рядом с aurora: сборка под /halo/, модули — общий каталог /usr/share/halo/modules
define Package/$(PKG_NAME)-preview/install
	$(INSTALL_DIR) $(1)/usr/share/aurora/halo
	$(CP) $(PKG_BUILD_DIR)/pkg-files-preview/* $(1)/usr/share/aurora/halo/
	$(LN) -sf /usr/share/halo/modules $(1)/usr/share/aurora/halo/modules
	$(call Halo/InstallCommon,$(1))
endef

# halo-modules: манифест, ссылки на CGI модулей в /usr/share/aurora/script и подключение
# /etc/lighttpd/halo.d в шаблон aurora; веб-сервер — перезапуск с ними
define Package/$(PKG_NAME)-preview/postinst
#!/bin/sh
sh "$${IPKG_INSTROOT}/usr/libexec/halo-modules"
[ -n "$${IPKG_INSTROOT}" ] && exit 0
/etc/init.d/lighttpd restart
exit 0
endef

# шаблон aurora — без halo.d, ссылки на CGI модулей — убрать (модули остаются в /usr/share/halo)
define Package/$(PKG_NAME)-preview/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
sh /usr/libexec/halo-modules --detach-aurora
exit 0
endef

define Package/$(PKG_NAME)-preview/postrm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] && exit 0
rm -f /usr/share/halo/modules/manifest.js
/etc/init.d/lighttpd restart
exit 0
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
$(eval $(call BuildPackage,$(PKG_NAME)-preview))

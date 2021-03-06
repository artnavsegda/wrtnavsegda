include $(TOPDIR)/rules.mk

PKG_NAME:=jerryscript
PKG_VERSION:=0.1.0
PKG_RELEASE=$(PKG_SOURCE_VERSION)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/jerryscript-project/jerryscript.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk
include $(INCLUDE_DIR)/host-build.mk

define Package/jerryscript
	SECTION:=irz
	CATEGORY:=IRZ-custom
	DEPENDS:=+libpthread
	TITLE:=JavaScript engine
endef

CMAKE_OPTIONS += -DCMAKE_INSTALL_PREFIX=/usr -DJERRY_PROFILE=es2015-subset -DJERRY_ERROR_MESSAGES=ON

define Package/jerryscript/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/bin/jerry $(1)/usr/bin
	$(INSTALL_DIR) $(1)/usr/lib/
endef

define Build/InstallDev
	$(INSTALL_DIR) $(1)/usr/include
	$(INSTALL_DIR) $(1)/usr/lib/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-compiler.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-config.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-core.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-debugger.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-debugger-transport.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-port-default.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-port.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-snapshot.h $(1)/usr/include
	$(INSTALL_DIR) $(1)/usr/include/jerryscript-ext/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/handler.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/module.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/debugger.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/arg.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/arg.impl.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/autorelease.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/autorelease.impl.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/ipkg-install/usr/include/jerryscript-ext/handle-scope.h $(1)/usr/include/jerryscript-ext
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/lib/libjerry-core.a $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/lib/libjerry-ext.a $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/lib/libjerry-libm.a $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/lib/libjerry-port-default.a $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/ipkg-install/usr/lib/libjerry-port-default-minimal.a $(1)/usr/lib/
endef

$(eval $(call BuildPackage,jerryscript))
$(eval $(call HostBuild))

include $(TOPDIR)/rules.mk

PKG_NAME:=replxx
PKG_VERSION:=0.1.0
PKG_RELEASE=$(PKG_SOURCE_VERSION)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/AmokHuginnsson/replxx.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk
include $(INCLUDE_DIR)/host-build.mk

define Package/replxx
	SECTION:=irz
	CATEGORY:=IRZ-custom
	DEPENDS:=+libpthread +libstdcpp
	TITLE:=Read Evaluate Print Loop ++
endef

define Package/replxx/install
	$(INSTALL_DIR) $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/libreplxx.so $(1)/usr/lib/
endef

define Build/InstallDev
	$(INSTALL_DIR) $(1)/usr/include
	$(INSTALL_DIR) $(1)/usr/lib/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/include/replxx.h $(1)/usr/include
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/include/replxx.hxx $(1)/usr/include
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/libreplxx.a $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/libreplxx.so $(1)/usr/lib/
endef

$(eval $(call BuildPackage,replxx))
$(eval $(call HostBuild))

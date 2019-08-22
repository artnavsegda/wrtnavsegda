include $(TOPDIR)/rules.mk

PKG_NAME:=libhello
PKG_VERSION:=1.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/artnavsegda/libnavsegda.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk
include $(INCLUDE_DIR)/host-build.mk

define Package/libhello
	SECTION:=examples
	CATEGORY:=Examples
	TITLE:=Hello, World library
endef

define Package/libhello/description
	A simple "Hello, world!" - library
endef

define Package/libhello/install
	$(INSTALL_DIR) $(1)/usr/lib/
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/libhello.so $(1)/usr/lib/
	ln -s libhello.so $(1)/usr/lib/libhello.so.0
endef

define Build/InstallDev
	$(INSTALL_DIR) $(1)/usr/include
	$(INSTALL_DIR) $(1)/usr/lib/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/src/hello.h $(1)/usr/include
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/libhello.so $(1)/usr/lib/
	ln -s libhello.so $(1)/usr/lib/libhello.so.0
endef

$(eval $(call BuildPackage,libhello))
$(eval $(call HostBuild))


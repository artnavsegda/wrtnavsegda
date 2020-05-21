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

define Package/jerryscript/install
	$(INSTALL_DIR) $(1)/usr/lib/
endef

define Build/Compile
	$(PKG_BUILD_DIR)/tools/build.py
endef

define Build/InstallDev
	$(INSTALL_DIR) $(1)/usr/include
	$(INSTALL_DIR) $(1)/usr/lib/
endef

$(eval $(call BuildPackage,jerryscript))
$(eval $(call HostBuild))

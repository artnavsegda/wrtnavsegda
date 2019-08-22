include $(TOPDIR)/rules.mk

PKG_NAME:=wjelement
PKG_VERSION:=0.1.0
PKG_RELEASE=$(PKG_SOURCE_VERSION)

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/netmail-open/wjelement.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

include $(INCLUDE_DIR)/package.mk
include $(INCLUDE_DIR)/cmake.mk
include $(INCLUDE_DIR)/host-build.mk

define Package/wjelement
				SECTION:=irz
				CATEGORY:=IRZ-custom
				DEPENDS:=+libpthread
				TITLE:=Warp JSON parser
endef

define Package/wjelement/install
				$(INSTALL_DIR) $(1)/usr/lib/
				$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/lib/libxpl.so $(1)/usr/lib/
				ln -s libxpl.so $(1)/usr/lib/libxpl.so.1
				$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/wjwriter/libwjwriter.so $(1)/usr/lib/
				ln -s libwjwriter.so $(1)/usr/lib/libwjwriter.so.1
				$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/wjreader/libwjreader.so $(1)/usr/lib/
				ln -s libwjreader.so $(1)/usr/lib/libwjreader.so.1
				$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/wjelement/libwjelement.so $(1)/usr/lib/
				ln -s libwjelement.so $(1)/usr/lib/libwjelement.so.1
endef

define Build/InstallDev
endef

$(eval $(call BuildPackage,wjelement))
$(eval $(call HostBuild))

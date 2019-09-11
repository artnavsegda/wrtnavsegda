include $(TOPDIR)/rules.mk

PKG_NAME:=zcore
PKG_VERSION:=1.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/artnavsegda/zcore.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

PKG_FIXUP:=autoreconf

include $(INCLUDE_DIR)/package.mk

define Package/zcore
	SECTION:=irz
	CATEGORY:=IRZ-custom
	DEPENDS:=+libpthread +libreadline +wjelement +libncurses
	TITLE:=Zenith iRX CLI interface
endef

define Package/zcore/description
	CLI(something)
endef

define Package/zcore/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/zcore $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/zfilter $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/zfilter2 $(1)/usr/bin
endef

$(eval $(call BuildPackage,zcore))


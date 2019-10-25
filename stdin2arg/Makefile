include $(TOPDIR)/rules.mk

PKG_NAME:=stdin2arg
PKG_VERSION:=1.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/artnavsegda/crossnavsegda.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

PKG_FIXUP:=autoreconf

include $(INCLUDE_DIR)/package.mk

define Package/stdin2arg
	SECTION:=irz
	CATEGORY:=IRZ-custom
	DEPENDS:=+libpthread
	TITLE:=stdin2arg helper utility
endef

define Package/stdin2arg/description
	stdin2arg helper utility
endef

define Package/stdin2arg/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/stdin2arg $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/printargs $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/forkexec $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/src/popen $(1)/usr/bin
endef

$(eval $(call BuildPackage,stdin2arg))


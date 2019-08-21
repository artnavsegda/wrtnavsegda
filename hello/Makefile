include $(TOPDIR)/rules.mk

PKG_NAME:=hello
PKG_VERSION:=1.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/artnavsegda/mipsnavsegda.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

include $(INCLUDE_DIR)/package.mk

define Package/hello
	SECTION:=examples
	CATEGORY:=Examples
	TITLE:=Hello, World!
endef

define Package/helloworld/description
	A simple "Hello, world!" -application.
endef

define Package/hello/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/hello $(1)/usr/bin
endef

$(eval $(call BuildPackage,hello))


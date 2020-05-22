include $(TOPDIR)/rules.mk

PKG_NAME:=jcli
PKG_VERSION:=1.0
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL:=git://github.com/artnavsegda/jclinavsegda.git
PKG_SOURCE_SUBDIR:=$(PKG_NAME)-$(PKG_VERSION)
PKG_SOURCE_VERSION:=master
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION)-$(PKG_SOURCE_VERSION).tar.gz

PKG_MAINTAINER=Art Navsegda <artnavsegda@gmail.com>

PKG_FIXUP:=autoreconf

include $(INCLUDE_DIR)/package.mk

define Package/jcli
	SECTION:=irz
	CATEGORY:=IRZ-custom
	DEPENDS:=+libpthread +libreadline +jerryscript +libncurses
	TITLE:=JavaScript-based CLI interface
endef

define Package/jcli/description
	CLI(JavaScript)
endef

# Package build instructions; invoke the target-specific compiler to first compile the source file, and then to link the file into the final executable
define Build/Compile
	$(TARGET_CC) $(TARGET_LDFLAGS) -o $(PKG_BUILD_DIR)/$1 src/main.c src/exception.c src/irz-module.c -flto -ljerry-core -ljerry-ext -ljerry-port-default -ljerry-libm -lreadline
endef

define Package/jcli/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/jcli $(1)/usr/bin
endef

$(eval $(call BuildPackage,jcli))

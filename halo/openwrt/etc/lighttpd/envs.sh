#!/bin/sh

[ -s /usr/share/horizont/lib/envs.sh ] && . /usr/share/horizont/lib/envs.sh

cat <<EOF
setenv.add-environment = (
	"PKG_STORAGE_PATH" => "$PKG_STORAGE_PATH",
	"REAL_TEMP_STORAGE_PATH" => "$REAL_TEMP_STORAGE_PATH",
	"TEMP_CERT_STORAGE_PATH" => "$TEMP_CERT_STORAGE_PATH",
	"TEMP_STORAGE_PATH" => "$TEMP_STORAGE_PATH",
	"PATH" => "$PATH"
)
EOF
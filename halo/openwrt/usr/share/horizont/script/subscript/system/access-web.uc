#!/usr/bin/ucode

import { parse_values, mapping, remapping, typify, service_status } from "horizont.utils";
const ubus = require("ubus").connect();
const ctx  = require("uci").cursor();

const OPTIONS_MAP = {
    // rudiments: _get still maps these uci keys on devices that still have them
    "use_http":     "use-http",
    "http_port":    "http-port",
    "use_https":    "use-https",
    "http_redir":   "redirect-to-https",

    "https_port":   "https-port",
    "tls":          "tls",
    "cert":         "cert"
};

const action = {
    _get: function() {
        let data = ubus.call('uci', 'get', {'config': 'lighttpd', 'type': 'server', 'section': 'main'} ).values;
        return mapping(data, OPTIONS_MAP);
    },
    
    _set: function(data) {
        data = parse_values();
        let val = {};
        val[data._option] = typify(data._value);

        val = remapping(val, OPTIONS_MAP);

        ubus.call('uci', 'set', {'config': 'lighttpd', 'section': 'main', 'values': val});
    },
    
    _apply: function() {
        system("(sleep 5; /etc/init.d/lighttpd restart)&>/dev/null&");
    },

    _status: function(data) {
        return service_status('lighttpd', 'instance1', 1);
    }
};

if (!length(ARGV))
    printf("%J\n", {'error': 'action not given'});

else {
    let cmd = '_' + shift(ARGV);

    if (!exists(action, cmd))
        printf("%J\n", {'error': 'unknown action'});
    
    else {
        let x = action[cmd]();
        if (x)
            printf("%J\n", x);
    }
}

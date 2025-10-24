# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

import os
import pwd
from pathlib import Path

# global dependencies
GLOBAL_DEPS = ["git", "wget", "curl", "unzip", "dfu-util", "python3-virtualenv"]

# strings
INVALID_CHOICE = "Invalid choice. Please select a valid value."

# current user
CURRENT_USER = pwd.getpwuid(os.getuid())[0]

# dirs
SYSTEMD = Path("/etc/systemd/system")
OPENRC = Path("/etc/init.d")
NGINX_SITES_AVAILABLE = Path("/etc/nginx/sites-available")
NGINX_SITES_ENABLED = Path("/etc/nginx/sites-enabled")


def _resolve_nginx_conf_dir() -> Path:
    """Return the NGINX include directory actually loaded by nginx."""

    candidate_dirs = (Path("/etc/nginx/conf.d"), Path("/etc/nginx/http.d"))
    nginx_conf = Path("/etc/nginx/nginx.conf")

    if nginx_conf.exists():
        try:
            config_text = nginx_conf.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            config_text = ""

        for candidate in candidate_dirs:
            if candidate.as_posix() in config_text:
                return candidate

    for candidate in candidate_dirs:
        if candidate.exists():
            return candidate

    return candidate_dirs[0]


NGINX_CONFD = _resolve_nginx_conf_dir()

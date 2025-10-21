# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from pathlib import Path

from utils.sys_utils import InitSystem, get_init_system, get_service_directory

# repo
CROWSNEST_REPO = "https://github.com/mainsail-crew/crowsnest.git"

# names
CROWSNEST_BASE_SERVICE_NAME = "crowsnest"
_INIT_SYSTEM = get_init_system()
CROWSNEST_SERVICE_NAME = (
    f"{CROWSNEST_BASE_SERVICE_NAME}.service"
    if _INIT_SYSTEM == InitSystem.SYSTEMD
    else CROWSNEST_BASE_SERVICE_NAME
)

# directories
CROWSNEST_DIR = Path.home().joinpath("crowsnest")
CROWSNEST_CONFIG_DIR = Path.home().joinpath("printer_data/config")
CROWSNEST_LOG_DIR = Path.home().joinpath("printer_data/logs")
CROWSNEST_ENV_DIR = Path.home().joinpath("printer_data/systemd")

# files
CROWSNEST_MULTI_CONFIG = CROWSNEST_DIR.joinpath("tools/.config")
CROWSNEST_INSTALL_SCRIPT = CROWSNEST_DIR.joinpath("tools/install.sh")
CROWSNEST_BIN_FILE = Path("/usr/local/bin/crowsnest")
CROWSNEST_LOGROTATE_FILE = Path("/etc/logrotate.d/crowsnest")
CROWSNEST_CONFIG_FILE = CROWSNEST_CONFIG_DIR.joinpath("crowsnest.conf")
CROWSNEST_LOG_FILE = CROWSNEST_LOG_DIR.joinpath("crowsnest.log")
CROWSNEST_ENV_FILE = CROWSNEST_ENV_DIR.joinpath("crowsnest.env")
CROWSNEST_SERVICE_FILE = get_service_directory().joinpath(
    CROWSNEST_SERVICE_NAME
    if _INIT_SYSTEM == InitSystem.SYSTEMD
    else CROWSNEST_BASE_SERVICE_NAME
)

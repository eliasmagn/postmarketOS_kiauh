# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from pathlib import Path

from utils.sys_utils import InitSystem, detect_init_system, get_service_directory

# repo
KLIPPERSCREEN_REPO = "https://github.com/KlipperScreen/KlipperScreen.git"

# names
def _resolve_service_name() -> str:
    init_system = detect_init_system()
    if init_system == InitSystem.OPENRC:
        return "KlipperScreen"
    return "KlipperScreen.service"


KLIPPERSCREEN_SERVICE_NAME = _resolve_service_name()
KLIPPERSCREEN_UPDATER_SECTION_NAME = "update_manager KlipperScreen"
KLIPPERSCREEN_LOG_NAME = "KlipperScreen.log"

# directories
KLIPPERSCREEN_DIR = Path.home().joinpath("KlipperScreen")
KLIPPERSCREEN_ENV_DIR = Path.home().joinpath(".KlipperScreen-env")

# files
KLIPPERSCREEN_REQ_FILE = KLIPPERSCREEN_DIR.joinpath(
    "scripts/KlipperScreen-requirements.txt"
)
KLIPPERSCREEN_INSTALL_SCRIPT = KLIPPERSCREEN_DIR.joinpath(
    "scripts/KlipperScreen-install.sh"
)
KLIPPERSCREEN_INSTALL_SCRIPT_ASSET = Path(__file__).parent.joinpath(
    "assets/KlipperScreen-install.sh"
)
KLIPPERSCREEN_SERVICE_FILE = get_service_directory().joinpath(KLIPPERSCREEN_SERVICE_NAME)

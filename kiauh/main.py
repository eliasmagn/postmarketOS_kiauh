# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
import io
import sys

from core.logger import Logger
from core.menus.main_menu import MainMenu
from core.settings.kiauh_settings import KiauhSettings
from utils.sudo_session import SudoSession


def ensure_encoding() -> None:
    if sys.stdout.encoding == "UTF-8" or not isinstance(sys.stdout, io.TextIOWrapper):
        return
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    sudo_session = SudoSession()
    try:
        KiauhSettings()
        ensure_encoding()
        sudo_session.maybe_enable()
        MainMenu().run()
    except KeyboardInterrupt:
        Logger.print_ok("\nHappy printing!\n", prefix=False)
    finally:
        sudo_session.close()


if __name__ == "__main__":
    main()

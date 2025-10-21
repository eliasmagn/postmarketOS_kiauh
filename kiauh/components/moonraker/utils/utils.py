# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
import json
import shutil
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, run
from typing import Dict, List, Optional

from components.moonraker import (
    MODULE_PATH,
    MOONRAKER_DEFAULT_PORT,
    MOONRAKER_DEPS_JSON_FILE,
    MOONRAKER_DIR,
    MOONRAKER_ENV_DIR,
    MOONRAKER_INSTALL_SCRIPT,
)
from components.moonraker.moonraker import Moonraker
from components.moonraker.utils.sysdeps_parser import SysDepsParser
from components.webui_client.base_data import BaseWebClient
from core.logger import Logger
from core.services.backup_service import BackupService
from core.submodules.simple_config_parser.src.simple_config_parser.simple_config_parser import (
    SimpleConfigParser,
)
from core.types.component_status import ComponentStatus
from utils.common import check_install_dependencies, get_install_status
from utils.fs_utils import create_symlink, remove_with_sudo
from utils.instance_utils import get_instances
from utils.sys_utils import (
    PackageManager,
    get_ipv4_addr,
    get_package_manager,
    has_package_equivalent,
    parse_packages_from_file,
)


APK_UPDATE_WRAPPER = MODULE_PATH.joinpath("assets/apk-update-manager-wrapper.py")
APK_UPDATE_TARGET = Path("/usr/local/lib/moonraker/apk-apt-wrapper")
APK_UPDATE_LINKS = {
    name: Path("/usr/local/bin").joinpath(name)
    for name in ("apt", "apt-get", "apt-cache")
}


def get_moonraker_status() -> ComponentStatus:
    return get_install_status(MOONRAKER_DIR, MOONRAKER_ENV_DIR, Moonraker)


def install_moonraker_packages() -> None:
    Logger.print_status("Parsing Moonraker system dependencies  ...")

    moonraker_deps: List[str] = []
    sysdeps: Dict[str, List[str]] = {}
    parser: SysDepsParser | None = None
    if MOONRAKER_DEPS_JSON_FILE.exists():
        Logger.print_info(
            f"Parsing system dependencies from {MOONRAKER_DEPS_JSON_FILE.name} ..."
        )
        parser = SysDepsParser()
        sysdeps = load_sysdeps_json(MOONRAKER_DEPS_JSON_FILE)
        moonraker_deps.extend(parser.parse_dependencies(sysdeps))

    elif MOONRAKER_INSTALL_SCRIPT.exists():
        Logger.print_warn(f"{MOONRAKER_DEPS_JSON_FILE.name} not found!")
        Logger.print_info(
            f"Parsing system dependencies from {MOONRAKER_INSTALL_SCRIPT.name} ..."
        )
        moonraker_deps = parse_packages_from_file(MOONRAKER_INSTALL_SCRIPT)

    if not moonraker_deps and sysdeps:
        manager = get_package_manager()
        if (
            manager == PackageManager.APK
            and parser is not None
            and "debian" in sysdeps
        ):
            Logger.print_warn(
                "Moonraker's system-dependencies.json does not define a postmarketOS/"
                "Alpine section. Reusing the Debian dependency list and translating it "
                "for apk."
            )
            moonraker_deps = sysdeps["debian"]

    if not moonraker_deps:
        raise ValueError("Error parsing Moonraker dependencies!")

    check_install_dependencies({*moonraker_deps})


def _sudo_run(command: List[str], error_message: str) -> bool:
    try:
        run(command, stderr=PIPE, stdout=DEVNULL, check=True)
    except CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode().strip()
        if stderr:
            error_message = f"{error_message}: {stderr}"
        Logger.print_error(error_message)
        return False
    return True


def ensure_apk_update_manager_dropin() -> bool:
    manager = get_package_manager()
    if manager != PackageManager.APK:
        return False

    if not APK_UPDATE_WRAPPER.exists():
        Logger.print_error(
            "Moonraker apk update manager wrapper is missing from the assets directory."
        )
        return False

    target_dir = APK_UPDATE_TARGET.parent
    if not _sudo_run(["sudo", "mkdir", "-p", target_dir.as_posix()], "Failed to create drop-in directory"):
        return False
    if not _sudo_run(
        ["sudo", "cp", "-f", APK_UPDATE_WRAPPER.as_posix(), APK_UPDATE_TARGET.as_posix()],
        "Failed to install apk update manager wrapper",
    ):
        return False
    if not _sudo_run(
        ["sudo", "chmod", "0755", APK_UPDATE_TARGET.as_posix()],
        "Failed to adjust apk update manager wrapper permissions",
    ):
        return False

    installed_links = True
    for link in APK_UPDATE_LINKS.values():
        try:
            create_symlink(APK_UPDATE_TARGET, link, sudo=True)
        except CalledProcessError as exc:
            Logger.print_error(f"Failed to create symlink for {link.name}: {exc}")
            installed_links = False
    if not installed_links:
        return False

    Logger.print_ok("Installed apk compatibility wrappers for Moonraker system updates.")
    return True


def remove_apk_update_manager_dropin() -> None:
    manager = get_package_manager()
    if manager != PackageManager.APK:
        return

    remove_with_sudo(list(APK_UPDATE_LINKS.values()))
    remove_with_sudo(APK_UPDATE_TARGET)


def remove_polkit_rules() -> bool:
    if not MOONRAKER_DIR.exists():
        log = "Cannot remove policykit rules. Moonraker directory not found."
        Logger.print_warn(log)
        return False

    try:
        cmd = [f"{MOONRAKER_DIR}/scripts/set-policykit-rules.sh", "--clear"]
        run(cmd, stderr=PIPE, stdout=DEVNULL, check=True)
        if get_package_manager() == PackageManager.APK:
            remove_apk_update_manager_dropin()
        return True
    except CalledProcessError as e:
        Logger.print_error(f"Error while removing policykit rules: {e}")
        return False


def create_example_moonraker_conf(
    instance: Moonraker,
    ports_map: Dict[str, int],
    clients: Optional[List[BaseWebClient]] = None,
) -> None:
    Logger.print_status(f"Creating example moonraker.conf in '{instance.base.cfg_dir}'")
    if instance.cfg_file.is_file():
        Logger.print_info(f"'{instance.cfg_file}' already exists.")
        return

    source = MODULE_PATH.joinpath("assets/moonraker.conf")
    target = instance.cfg_file
    try:
        shutil.copy(source, target)
    except OSError as e:
        Logger.print_error(f"Unable to create example moonraker.conf:\n{e}")
        return

    ports = [
        ports_map.get(instance)
        for instance in ports_map
        if ports_map.get(instance) is not None
    ]
    if ports_map.get(instance.suffix) is None:
        # this could be improved to not increment the max value of the ports list and assign it as the port
        # as it can lead to situation where the port for e.g. instance moonraker-2 becomes 7128 if the port
        # of moonraker-1 is 7125 and moonraker-3 is 7127 and there are moonraker.conf files for moonraker-1
        # and moonraker-3 already. though, there does not seem to be a very reliable way of always assigning
        # the correct port to each instance and the user will likely be required to correct the value manually.
        port = max(ports) + 1 if ports else MOONRAKER_DEFAULT_PORT
    else:
        port = ports_map.get(instance.suffix)

    ports_map[instance.suffix] = port

    ip = get_ipv4_addr().split(".")[:2]
    ip.extend(["0", "0/16"])
    uds = instance.base.comms_dir.joinpath("klippy.sock")

    scp = SimpleConfigParser()
    scp.read_file(target)
    trusted_clients: List[str] = [
        f"    {'.'.join(ip)}\n",
        *scp.getvals("authorization", "trusted_clients"),
    ]

    scp.set_option("server", "port", str(port))
    scp.set_option("server", "klippy_uds_address", str(uds))
    scp.set_option("authorization", "trusted_clients", trusted_clients)

    manager = get_package_manager()
    if manager == PackageManager.APK:
        Logger.print_info(
            "Configuring Moonraker to use the apk compatibility drop-in for system updates."
        )
        scp.set_option("update_manager", "enable_packagekit", "False")
    elif not has_package_equivalent("packagekit", manager):
        Logger.print_info(
            "PackageKit is unavailable on this platform; Moonraker system updates "
            "will be disabled in the generated configuration."
        )
        scp.set_option("update_manager", "enable_system_updates", "False")

    # add existing client and client configs in the update section
    if clients is not None and len(clients) > 0:
        for c in clients:
            # client part
            c_section = f"update_manager {c.name}"
            c_options = [
                ("type", "web"),
                ("channel", "stable"),
                ("repo", c.repo_path),
                ("path", c.client_dir),
            ]
            scp.add_section(section=c_section)
            for option in c_options:
                scp.set_option(c_section, option[0], option[1])

            # client config part
            c_config = c.client_config
            if c_config.config_dir.exists():
                c_config_section = f"update_manager {c_config.name}"
                c_config_options = [
                    ("type", "git_repo"),
                    ("primary_branch", "master"),
                    ("path", c_config.config_dir),
                    ("origin", c_config.repo_url),
                    ("managed_services", "klipper"),
                ]
                scp.add_section(section=c_config_section)
                for option in c_config_options:
                    scp.set_option(c_config_section, option[0], option[1])

    scp.write_file(target)
    if manager == PackageManager.APK:
        configure_apk_update_manager([instance])
    Logger.print_ok(f"Example moonraker.conf created in '{instance.base.cfg_dir}'")


def configure_apk_update_manager(
    instances: Optional[List[Moonraker]] = None,
) -> bool:
    manager = get_package_manager()
    if manager != PackageManager.APK:
        return False

    if not ensure_apk_update_manager_dropin():
        return False

    if not instances:
        instances = get_instances(Moonraker)

    if not instances:
        return True

    updated_any = False
    for instance in instances:
        cfg_path = instance.cfg_file
        if not cfg_path.exists():
            continue

        scp = SimpleConfigParser()
        scp.read_file(cfg_path)
        updated = False
        if scp.getval("update_manager", "enable_system_updates", fallback="True") == "False":
            scp.set_option("update_manager", "enable_system_updates", "True")
            updated = True
        if scp.getval("update_manager", "enable_packagekit", fallback="True") != "False":
            scp.set_option("update_manager", "enable_packagekit", "False")
            updated = True

        if updated:
            scp.write_file(cfg_path)
            updated_any = True

    if updated_any:
        Logger.print_info(
            "Configured Moonraker to use apk-backed system updates via the apt compatibility drop-in."
        )

    return True


def disable_system_updates(instances: Optional[List[Moonraker]] = None) -> None:
    manager = get_package_manager()
    if manager == PackageManager.APK or has_package_equivalent("packagekit", manager):
        return

    if not instances:
        instances = get_instances(Moonraker)

    if not instances:
        return

    updated = False
    for instance in instances:
        cfg_path = instance.cfg_file
        if not cfg_path.exists():
            continue

        scp = SimpleConfigParser()
        scp.read_file(cfg_path)
        if scp.getval("update_manager", "enable_system_updates", fallback="True") == "False":
            continue
        scp.set_option("update_manager", "enable_system_updates", "False")
        scp.write_file(cfg_path)
        updated = True

    if updated:
        Logger.print_info(
            "Moonraker system update provider disabled because PackageKit is not available on this platform."
        )


def backup_moonraker_dir() -> None:
    svc = BackupService()
    svc.backup_directory(
        source_path=MOONRAKER_DIR, backup_name="moonraker", target_path="moonraker"
    )
    svc.backup_directory(
        source_path=MOONRAKER_ENV_DIR,
        backup_name="moonraker-env",
        target_path="moonraker",
    )


def backup_moonraker_db_dir() -> None:
    instances: List[Moonraker] = get_instances(Moonraker)
    svc = BackupService()

    if not instances:
        # fallback: search for printer data directories in the user's home directory
        Logger.print_info("No Moonraker instances found via systemd services.")
        Logger.print_info(
            "Attempting to find printer data directories in home directory..."
        )

        home_dir = Path.home()
        printer_data_dirs = []

        for pattern in ["printer_data", "printer_*_data"]:
            for data_dir in home_dir.glob(pattern):
                if data_dir.is_dir():
                    printer_data_dirs.append(data_dir)

        if not printer_data_dirs:
            Logger.print_info("Unable to find directory to backup!")
            Logger.print_info("No printer data directories found in home directory.")
            return

        for data_dir in printer_data_dirs:
            svc.backup_directory(
                source_path=data_dir.joinpath("database"),
                target_path=data_dir.name,
                backup_name="database",
            )

        return

    for instance in instances:
        svc.backup_directory(
            source_path=instance.db_dir,
            target_path=f"{instance.data_dir.name}",
            backup_name="database",
        )


def load_sysdeps_json(file: Path) -> Dict[str, List[str]]:
    try:
        sysdeps: Dict[str, List[str]] = json.loads(file.read_bytes())
    except json.JSONDecodeError as e:
        Logger.print_error(f"Unable to parse {file.name}:\n{e}")
        return {}
    else:
        return sysdeps

# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path
from subprocess import DEVNULL, CalledProcessError, run
from typing import List, Set

from components.crowsnest import (
    CROWSNEST_BASE_SERVICE_NAME,
    CROWSNEST_BIN_FILE,
    CROWSNEST_DIR,
    CROWSNEST_INSTALL_SCRIPT,
    CROWSNEST_CONFIG_DIR,
    CROWSNEST_CONFIG_FILE,
    CROWSNEST_ENV_DIR,
    CROWSNEST_ENV_FILE,
    CROWSNEST_LOGROTATE_FILE,
    CROWSNEST_LOG_DIR,
    CROWSNEST_LOG_FILE,
    CROWSNEST_MULTI_CONFIG,
    CROWSNEST_REPO,
    CROWSNEST_SERVICE_FILE,
    CROWSNEST_SERVICE_NAME,
)
from components.klipper.klipper import Klipper
from core.constants import CURRENT_USER
from core.logger import DialogType, Logger
from core.services.backup_service import BackupService
from core.settings.kiauh_settings import KiauhSettings
from core.types.component_status import ComponentStatus
from utils.common import (
    check_install_dependencies,
    get_install_status,
)
from utils.git_utils import (
    git_clone_wrapper,
    git_pull_wrapper,
)
from utils.input_utils import get_confirm
from utils.instance_utils import get_instances
from utils.sys_utils import (
    InitSystem,
    PackageManager,
    cmd_sysctl_service,
    cmd_sysctl_manage,
    create_env_file,
    create_service_file,
    get_init_system,
    get_package_manager,
    parse_packages_from_file,
    remove_system_service,
)
from utils.sudo_session import ensure_sudo_session


def install_crowsnest() -> None:
    # Step 1: Clone crowsnest repo
    git_clone_wrapper(CROWSNEST_REPO, CROWSNEST_DIR, "master")

    init_system = get_init_system()
    package_manager = get_package_manager()

    # Step 2: Install dependencies
    dependency_list: Set[str] = {"make"}
    pkglist_generic = CROWSNEST_DIR.joinpath("tools/libs/pkglist-generic.sh")
    if pkglist_generic.exists():
        dependency_list.update(parse_packages_from_file(pkglist_generic))
    check_install_dependencies(dependency_list, include_global=False)

    # Step 3: Check for Multi Instance
    instances: List[Klipper] = get_instances(Klipper)

    if len(instances) > 1:
        print_multi_instance_warning(instances)

        if not get_confirm("Do you want to continue with the installation?"):
            Logger.print_info("Crowsnest installation aborted!")
            return

        Logger.print_status("Launching crowsnest's install configurator ...")
        time.sleep(3)
        configure_multi_instance()

    if package_manager == PackageManager.APK:
        _install_crowsnest_apk(init_system)
        return

    # Step 4: Launch crowsnest installer
    Logger.print_status("Launching crowsnest installer ...")
    Logger.print_info("Installer will prompt you for sudo password!")
    try:
        run(
            "sudo make install",
            cwd=CROWSNEST_DIR,
            shell=True,
            check=True,
        )
    except CalledProcessError as e:
        Logger.print_error(f"Something went wrong! Please try again...\n{e}")
        return


def print_multi_instance_warning(instances: List[Klipper]) -> None:
    Logger.print_dialog(
        DialogType.WARNING,
        [
            "Multi instance install detected!",
            "\n\n",
            "Crowsnest is NOT designed to support multi instances. A workaround "
            "for this is to choose the most used instance as a 'master' and use "
            "this instance to set up your 'crowsnest.conf' and steering it's service.",
            "\n\n",
            "The following instances were found:",
            *[f"● {instance.data_dir.name}" for instance in instances],
        ],
    )


def configure_multi_instance() -> None:
    try:
        run(
            "make config",
            cwd=CROWSNEST_DIR,
            shell=True,
            check=True,
        )
    except CalledProcessError as e:
        Logger.print_error(f"Something went wrong! Please try again...\n{e}")
        if CROWSNEST_MULTI_CONFIG.exists():
            Path.unlink(CROWSNEST_MULTI_CONFIG)
        return

    if not CROWSNEST_MULTI_CONFIG.exists():
        Logger.print_error("Generating .config failed, installation aborted")


def update_crowsnest() -> None:
    try:
        service_name = (
            CROWSNEST_SERVICE_NAME
            if get_init_system() == InitSystem.SYSTEMD
            else CROWSNEST_BASE_SERVICE_NAME
        )
        cmd_sysctl_service(service_name, "stop")

        if not CROWSNEST_DIR.exists():
            git_clone_wrapper(CROWSNEST_REPO, CROWSNEST_DIR, "master")
        else:
            Logger.print_status("Updating Crowsnest ...")

            settings = KiauhSettings()
            if settings.kiauh.backup_before_update:
                svc = BackupService()
                svc.backup_directory(
                    source_path=CROWSNEST_DIR,
                    target_path="crowsnest",
                    backup_name="crowsnest",
                )

            git_pull_wrapper(CROWSNEST_DIR)

            deps = set(parse_packages_from_file(CROWSNEST_INSTALL_SCRIPT))
            pkglist_generic = CROWSNEST_DIR.joinpath("tools/libs/pkglist-generic.sh")
            if pkglist_generic.exists():
                deps.update(parse_packages_from_file(pkglist_generic))
            check_install_dependencies(deps, include_global=False)

            Logger.print_status("Rebuilding Crowsnest backends ...")
            run(
                ["bash", "bin/build.sh", "--build"],
                cwd=CROWSNEST_DIR,
                check=True,
            )

        cmd_sysctl_service(service_name, "start")

        Logger.print_ok("Crowsnest updated successfully.", end="\n\n")
    except CalledProcessError as e:
        Logger.print_error(f"Something went wrong! Please try again...\n{e}")
        return


def get_crowsnest_status() -> ComponentStatus:
    files = [
        CROWSNEST_BIN_FILE,
        CROWSNEST_LOGROTATE_FILE,
        CROWSNEST_SERVICE_FILE,
    ]
    return get_install_status(CROWSNEST_DIR, files=files)


def remove_crowsnest() -> None:
    if not CROWSNEST_DIR.exists():
        Logger.print_info("Crowsnest does not seem to be installed! Skipping ...")
        return

    package_manager = get_package_manager()
    init_system = get_init_system()

    if package_manager == PackageManager.APK:
        _remove_crowsnest_apk(init_system)
    else:
        try:
            run(
                "make uninstall",
                cwd=CROWSNEST_DIR,
                shell=True,
                check=True,
            )
        except CalledProcessError as e:
            Logger.print_error(f"Something went wrong! Please try again...\n{e}")
            return

        Logger.print_status("Removing crowsnest directory ...")
        shutil.rmtree(CROWSNEST_DIR)
        Logger.print_ok("Directory removed!")


def _render_template(template: Path, replacements: dict[str, str]) -> str:
    content = template.read_text()
    for key, value in replacements.items():
        content = content.replace(key, value)
    return content


def _write_root_file(target: Path, content: str) -> None:
    ensure_sudo_session()
    run(
        ["sudo", "tee", target],
        input=content.encode(),
        stdout=DEVNULL,
        check=True,
    )


def _ensure_directories(paths: List[Path]) -> None:
    for directory in paths:
        directory.mkdir(parents=True, exist_ok=True)


def _install_crowsnest_apk(init_system: InitSystem) -> None:
    Logger.print_status("Installing Crowsnest using apk workflow ...")
    _ensure_directories([CROWSNEST_CONFIG_DIR, CROWSNEST_LOG_DIR, CROWSNEST_ENV_DIR])

    Logger.print_status("Deploying crowsnest executable ...")
    ensure_sudo_session()
    run(
        ["sudo", "install", "-m", "755", CROWSNEST_DIR.joinpath("crowsnest"), CROWSNEST_BIN_FILE],
        check=True,
    )
    Logger.print_ok("Executable installed.")

    logrotate_template = CROWSNEST_DIR.joinpath("resources/logrotate_crowsnest")
    if logrotate_template.exists():
        Logger.print_status("Installing logrotate rule ...")
        logrotate_content = _render_template(
            logrotate_template,
            {"%LOGPATH%": str(CROWSNEST_LOG_FILE)},
        )
        _write_root_file(CROWSNEST_LOGROTATE_FILE, logrotate_content)
        Logger.print_ok("Logrotate rule installed.")

    Logger.print_status("Writing environment configuration ...")
    env_template = CROWSNEST_DIR.joinpath("resources/crowsnest.env")
    env_content = _render_template(env_template, {"%CONFPATH%": str(CROWSNEST_CONFIG_DIR)})
    create_env_file(CROWSNEST_ENV_FILE, env_content)

    Logger.print_status("Writing crowsnest configuration ...")
    config_template = CROWSNEST_DIR.joinpath("resources/crowsnest.conf")
    if CROWSNEST_CONFIG_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = CROWSNEST_CONFIG_FILE.with_suffix(f"{CROWSNEST_CONFIG_FILE.suffix}.{timestamp}")
        shutil.move(CROWSNEST_CONFIG_FILE, backup)
        Logger.print_info(f"Existing configuration backed up as {backup}")
    config_content = _render_template(
        config_template,
        {"%LOGPATH%": str(CROWSNEST_LOG_FILE)},
    )
    CROWSNEST_CONFIG_FILE.write_text(config_content)

    Logger.print_status("Building streaming backends ...")
    run(["bash", "bin/build.sh", "--build"], cwd=CROWSNEST_DIR, check=True)

    _ensure_video_group_membership()

    Logger.print_status("Creating service definition ...")
    if init_system == InitSystem.SYSTEMD:
        service_template = CROWSNEST_DIR.joinpath("resources/crowsnest.service")
        service_content = _render_template(
            service_template,
            {
                "%USER%": CURRENT_USER,
                "%ENV%": str(CROWSNEST_ENV_FILE),
            },
        )
        create_service_file(f"{CROWSNEST_BASE_SERVICE_NAME}.service", service_content)
    else:
        create_service_file(
            CROWSNEST_BASE_SERVICE_NAME,
            _render_openrc_service(),
        )

    cmd_sysctl_manage("daemon-reload")
    service_name = (
        CROWSNEST_SERVICE_NAME
        if init_system == InitSystem.SYSTEMD
        else CROWSNEST_BASE_SERVICE_NAME
    )
    cmd_sysctl_service(service_name, "enable")
    cmd_sysctl_service(service_name, "start")
    Logger.print_ok("Crowsnest installation complete.")


def _render_openrc_service() -> str:
    return f"""#!/sbin/openrc-run

description=\"crowsnest webcam service\"
command=\"/usr/local/bin/crowsnest\"
command_user=\"{CURRENT_USER}\"
command_background=\"yes\"
supervisor=supervise-daemon
pidfile=\"/run/$RC_SVCNAME.pid\"
command_chdir=\"{CROWSNEST_DIR}\"

depend() {{
    need localmount
    use net
    before nginx
}}

load_env() {{
    if [ -f \"{CROWSNEST_ENV_FILE}\" ]; then
        set -a
        . \"{CROWSNEST_ENV_FILE}\"
        set +a
    fi
    command_args=\"${{CROWSNEST_ARGS:-}}\"
}}

start_pre() {{
    load_env
}}

stop_pre() {{
    load_env
}}
"""


def _ensure_video_group_membership() -> None:
    try:
        group_check = run(
            ["id", "-nG", CURRENT_USER],
            capture_output=True,
            text=True,
            check=True,
        )
        groups = group_check.stdout.split()
        if "video" not in groups:
            Logger.print_status(f"Adding user '{CURRENT_USER}' to group 'video' ...")
            ensure_sudo_session()
            run(["sudo", "usermod", "-a", "-G", "video", CURRENT_USER], check=True)
            Logger.print_ok("User added to group 'video'.")
        else:
            Logger.print_info(f"User '{CURRENT_USER}' already in group 'video'.")
    except (CalledProcessError, FileNotFoundError) as error:
        message = (
            f"Unable to ensure video group membership automatically: {error}".replace(
                "\n", " "
            )
        )
        Logger.print_warn(message)


def _remove_crowsnest_apk(init_system: InitSystem) -> None:
    service_name = (
        CROWSNEST_SERVICE_NAME
        if init_system == InitSystem.SYSTEMD
        else CROWSNEST_BASE_SERVICE_NAME
    )

    try:
        remove_system_service(service_name)
    except Exception as error:
        Logger.print_warn(f"Failed to remove service cleanly: {error}")

    for path in (CROWSNEST_BIN_FILE, CROWSNEST_LOGROTATE_FILE):
        if path.exists():
            Logger.print_status(f"Removing {path} ...")
            ensure_sudo_session()
            run(["sudo", "rm", "-f", path], check=True)

    if CROWSNEST_ENV_FILE.exists():
        Logger.print_status("Removing environment file ...")
        CROWSNEST_ENV_FILE.unlink()

    Logger.print_status("Removing crowsnest directory ...")
    shutil.rmtree(CROWSNEST_DIR)
    Logger.print_ok("Directory removed!")

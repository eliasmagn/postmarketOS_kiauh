# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import os
import re
import select
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from enum import Enum
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, Popen, check_output, run
from typing import Iterable, List, Literal, Set, Tuple

from core.constants import SYSTEMD
from core.logger import Logger
from utils.fs_utils import check_file_exist, remove_with_sudo
from utils.input_utils import get_confirm

SysCtlServiceAction = Literal[
    "start",
    "stop",
    "restart",
    "reload",
    "enable",
    "disable",
    "mask",
    "unmask",
]
SysCtlManageAction = Literal["daemon-reload", "reset-failed"]


class VenvCreationFailedException(Exception):
    pass


class PackageManager(Enum):
    APT = "apt"
    APK = "apk"
    UNKNOWN = "unknown"


@lru_cache(maxsize=1)
def get_package_manager() -> PackageManager:
    if shutil.which("apt-get") and shutil.which("dpkg-query"):
        return PackageManager.APT
    if shutil.which("apk"):
        return PackageManager.APK
    return PackageManager.UNKNOWN


PACKAGE_TRANSLATIONS = {
    PackageManager.APK: {
        "python3-virtualenv": "py3-virtualenv",
        "python3-pip": "py3-pip",
        "python3-dev": "python3-dev",
        "python3-setuptools": "py3-setuptools",
        "python3-numpy": "py3-numpy",
        "python3-matplotlib": "py3-matplotlib",
        "libatlas-base-dev": "atlas-dev",
        "libopenblas-dev": "openblas-dev",
        "libyaml-dev": "yaml-dev",
        "build-essential": "build-base",
        "dpkg-dev": "dpkg",
    }
}


def resolve_package_names(packages: Iterable[str], manager: PackageManager) -> List[str]:
    translations = PACKAGE_TRANSLATIONS.get(manager, {})
    resolved: List[str] = []
    for package in packages:
        mapped = translations.get(package, package)
        if isinstance(mapped, (list, tuple, set)):
            for item in mapped:
                if item not in resolved:
                    resolved.append(item)
        else:
            if mapped not in resolved:
                resolved.append(mapped)
    return resolved


def kill(opt_err_msg: str = "") -> None:
    """
    Kills the application |
    :param opt_err_msg: an optional, additional error message
    :return: None
    """

    if opt_err_msg:
        Logger.print_error(opt_err_msg)
    Logger.print_error("A critical error has occured. KIAUH was terminated.")
    sys.exit(1)


def check_python_version(major: int, minor: int) -> bool:
    """
    Checks the python version and returns True if it's at least the given version
    :param major: the major version to check
    :param minor: the minor version to check
    :return: bool
    """
    if not (sys.version_info.major >= major and sys.version_info.minor >= minor):
        Logger.print_error("Versioncheck failed!")
        Logger.print_error(f"Python {major}.{minor} or newer required.")
        return False
    return True


def parse_packages_from_file(source_file: Path) -> List[str]:
    """
    Read the package names from bash scripts, when defined like:
    PKGLIST="package1 package2 package3" |
    :param source_file: path of the sourcefile to read from
    :return: A list of package names
    """

    packages = []
    with open(source_file, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("PKGLIST="):
                line = line.replace('"', "")
                line = line.replace("PKGLIST=", "")
                line = line.replace("${PKGLIST}", "")
                packages.extend(line.split())

    return packages


def create_python_venv(
    target: Path,
    force: bool = False,
    allow_access_to_system_site_packages: bool = False,
    use_python_binary: str | None = None
) -> bool:
    """
    Create a python 3 virtualenv at the provided target destination.
    Returns True if the virtualenv was created successfully.
    Returns False if the virtualenv already exists, recreation was declined or creation failed.
    :param target: Path where to create the virtualenv at
    :param force: Force recreation of the virtualenv
    :param allow_access_to_system_site_packages: give the virtual environment access to the system site-packages dir
    :param use_python_binary: allows to override default python binary
    :return: bool
    """
    Logger.print_status("Set up Python virtual environment ...")
    # If binarry override is not set, we use default defined here
    python_binary = use_python_binary if use_python_binary else "/usr/bin/python3"
    cmd = ["virtualenv", "-p", python_binary, target.as_posix()]
    cmd.append(
        "--system-site-packages"
    ) if allow_access_to_system_site_packages else None

    n = 2
    while(n > 0):
        if not target.exists():
            try:
                run(cmd, check=True)
                Logger.print_ok("Setup of virtualenv successful!")
                return True
            except CalledProcessError as e:
                Logger.print_error(f"Error setting up virtualenv:\n{e}")
                return False
        else:
            if n == 1:
                # This case should never happen, 
                # but the function should still behave correctly
                Logger.print_error("Virtualenv still exists after deletion.")
                return False                            
            if not force and not get_confirm(
                "Virtualenv already exists. Re-create?", default_choice=False
            ):
                Logger.print_info("Skipping re-creation of virtualenv ...")
                return False

            try:
                shutil.rmtree(target)
                n -= 1
            except OSError as e:
                log = f"Error removing existing virtualenv: {e.strerror}"
                Logger.print_error(log, False)
                return False


def update_python_pip(target: Path) -> None:
    """
    Updates pip in the provided target destination |
    :param target: Path of the virtualenv
    :return: None
    """
    Logger.print_status("Updating pip ...")
    try:
        pip_location: Path = target.joinpath("bin/pip")
        pip_exists: bool = check_file_exist(pip_location)

        if not pip_exists:
            raise FileNotFoundError("Error updating pip! Not found.")

        command = [pip_location.as_posix(), "install", "-U", "pip"]
        result = run(command, stderr=PIPE, text=True)
        if result.returncode != 0 or result.stderr:
            Logger.print_error(f"{result.stderr}", False)
            Logger.print_error("Updating pip failed!")
            return

        Logger.print_ok("Updating pip successful!")
    except FileNotFoundError as e:
        Logger.print_error(e)
        raise
    except CalledProcessError as e:
        Logger.print_error(f"Error updating pip:\n{e.output.decode()}")
        raise


def install_python_requirements(target: Path, requirements: Path) -> None:
    """
    Installs the python packages based on a provided requirements.txt |
    :param target: Path of the virtualenv
    :param requirements: Path to the requirements.txt file
    :return: None
    """
    try:
        Logger.print_status("Installing Python requirements ...")
        command = [
            target.joinpath("bin/pip").as_posix(),
            "install",
            "-r",
            f"{requirements}",
        ]
        result = run(command, stderr=PIPE, text=True)

        if result.returncode != 0:
            Logger.print_error(f"{result.stderr}", False)
            raise VenvCreationFailedException("Installing Python requirements failed!")

        Logger.print_ok("Installing Python requirements successful!")

    except Exception as e:
        log = f"Error installing Python requirements: {e}"
        Logger.print_error(log)
        raise VenvCreationFailedException(log)


def install_python_packages(target: Path, packages: List[str]) -> None:
    """
    Installs the python packages based on a provided packages list |
    :param target: Path of the virtualenv
    :param packages: str list of required packages
    :return: None
    """
    try:
        Logger.print_status("Installing Python requirements ...")
        command = [
            target.joinpath("bin/pip").as_posix(),
            "install",
        ]
        for pkg in packages:
            command.append(pkg)
        result = run(command, stderr=PIPE, text=True)

        if result.returncode != 0:
            Logger.print_error(f"{result.stderr}", False)
            raise VenvCreationFailedException("Installing Python requirements failed!")

        Logger.print_ok("Installing Python requirements successful!")

    except Exception as e:
        log = f"Error installing Python requirements: {e}"
        Logger.print_error(log)
        raise VenvCreationFailedException(log)


def update_system_package_lists(silent: bool, rls_info_change=False) -> None:
    """
    Updates the systems package list |
    :param silent: Log info to the console or not
    :param rls_info_change: Flag for "--allow-releaseinfo-change"
    :return: None
    """
    manager = get_package_manager()

    if manager == PackageManager.APT:
        cache_mtime: float = 0
        cache_files: List[Path] = [
            Path("/var/lib/apt/periodic/update-success-stamp"),
            Path("/var/lib/apt/lists"),
        ]
        for cache_file in cache_files:
            if cache_file.exists():
                cache_mtime = max(cache_mtime, os.path.getmtime(cache_file))

        update_age = int(time.time() - cache_mtime)
        update_interval = 6 * 3600  # 48hrs

        if update_age <= update_interval:
            return

        if not silent:
            Logger.print_status("Updating package list...")

        try:
            command = ["sudo", "apt-get", "update"]
            if rls_info_change:
                command.append("--allow-releaseinfo-change")

            result = run(command, stderr=PIPE, text=True)
            if result.returncode != 0 or result.stderr:
                Logger.print_error(f"{result.stderr}", False)
                Logger.print_error("Updating system package list failed!")
                return

            Logger.print_ok("System package list update successful!")
        except CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
            Logger.print_error(f"Error updating system package list:\n{stderr}")
            raise

    elif manager == PackageManager.APK:
        if not silent:
            Logger.print_status("Updating package list...")

        try:
            command = ["sudo", "apk", "update"]
            result = run(command, stderr=PIPE, text=True)
            if result.returncode != 0:
                Logger.print_error(f"{result.stderr}", False)
                Logger.print_error("Updating system package list failed!")
                return

            Logger.print_ok("System package list update successful!")
        except CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
            Logger.print_error(f"Error updating system package list:\n{stderr}")
            raise

    else:
        Logger.print_warn("Unsupported package manager. Skipping package list update.")


def get_upgradable_packages() -> List[str]:
    """
    Reads all system packages that can be upgraded.
    :return: A list of package names available for upgrade
    """
    manager = get_package_manager()

    try:
        if manager == PackageManager.APT:
            command = ["apt", "list", "--upgradable"]
            output: str = check_output(command, stderr=DEVNULL, text=True, encoding="utf-8")
            pkglist = []
            for line in output.split("\n"):
                if "/" not in line:
                    continue
                pkg = line.split("/")[0]
                pkglist.append(pkg)
            return pkglist

        if manager == PackageManager.APK:
            command = ["apk", "version", "-l", "<"]
            output = check_output(command, stderr=DEVNULL, text=True, encoding="utf-8")
            pkglist = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                pkg = line.split()[0]
                if pkg and pkg not in pkglist:
                    pkglist.append(pkg)
            return pkglist

        Logger.print_warn("Unsupported package manager. Cannot determine upgradable packages.")
        return []
    except CalledProcessError as e:
        raise Exception(f"Error reading upgradable packages: {e}")


def check_package_install(packages: Set[str]) -> List[str]:
    """
    Checks the system for installed packages |
    :param packages: List of strings of package names
    :return: A list containing the names of packages that are not installed
    """
    manager = get_package_manager()
    packages_to_check = resolve_package_names(packages, manager)

    not_installed: List[str] = []

    if manager == PackageManager.APT:
        for package in packages_to_check:
            command = ["dpkg-query", "-f'${Status}'", "--show", package]
            result = run(
                command,
                stdout=PIPE,
                stderr=DEVNULL,
                text=True,
            )
            if "installed" not in result.stdout.strip("'").split():
                not_installed.append(package)

    elif manager == PackageManager.APK:
        for package in packages_to_check:
            command = ["apk", "info", "-e", package]
            result = run(
                command,
                stdout=PIPE,
                stderr=DEVNULL,
                text=True,
            )
            if result.returncode != 0:
                not_installed.append(package)

    else:
        Logger.print_warn("Unsupported package manager. Assuming packages are missing.")
        not_installed.extend(packages_to_check)

    return not_installed


def install_system_packages(packages: List[str]) -> None:
    """
    Installs a list of system packages |
    :param packages: List of system package names
    :return: None
    """
    if not packages:
        return

    manager = get_package_manager()
    packages_to_install = resolve_package_names(packages, manager)

    try:
        if manager == PackageManager.APT:
            command = ["sudo", "apt-get", "install", "-y"] + packages_to_install
            run(command, stderr=PIPE, check=True)
        elif manager == PackageManager.APK:
            command = ["sudo", "apk", "add", "--no-cache"] + packages_to_install
            run(command, stderr=PIPE, check=True, text=True)
        else:
            raise RuntimeError("Unsupported package manager")

        Logger.print_ok("Packages successfully installed.")
    except CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
        Logger.print_error(f"Error installing packages:\n{stderr}")
        raise
    except RuntimeError as e:
        Logger.print_error(str(e))
        raise


def upgrade_system_packages(packages: List[str]) -> None:
    """
    Updates a list of system packages |
    :param packages: List of system package names
    :return: None
    """
    if not packages:
        return

    manager = get_package_manager()
    packages_to_upgrade = resolve_package_names(packages, manager)

    try:
        if manager == PackageManager.APT:
            command = ["sudo", "apt-get", "upgrade", "-y"] + packages_to_upgrade
            run(command, stderr=PIPE, check=True)
        elif manager == PackageManager.APK:
            command = ["sudo", "apk", "upgrade"] + packages_to_upgrade
            run(command, stderr=PIPE, check=True, text=True)
        else:
            raise RuntimeError("Unsupported package manager")

        Logger.print_ok("Packages successfully upgraded.")
    except CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, (bytes, bytearray)) else e.stderr
        raise Exception(f"Error upgrading packages:\n{stderr}")
    except RuntimeError as e:
        raise Exception(str(e))


# this feels hacky and not quite right, but for now it works
# see: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
def get_ipv4_addr() -> str:
    """
    Helper function that returns the IPv4 of the current machine
    by opening a socket and sending a package to an arbitrary IP. |
    :return: Local IPv4 of the current machine
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(("192.255.255.255", 1))
        ipv4: str = str(s.getsockname()[0])
        s.close()
        return ipv4
    except Exception:
        s.close()
        return "127.0.0.1"


def download_file(url: str, target: Path, show_progress=True) -> None:
    """
    Helper method for downloading files from a provided URL |
    :param url: the url to the file
    :param target: the target path incl filename
    :param show_progress: show download progress or not
    :return: None
    """
    try:
        if show_progress:
            urllib.request.urlretrieve(url, target, download_progress)
            sys.stdout.write("\n")
        else:
            urllib.request.urlretrieve(url, target)
    except urllib.error.HTTPError as e:
        Logger.print_error(f"Download failed! HTTP error occured: {e}")
        raise
    except urllib.error.URLError as e:
        Logger.print_error(f"Download failed! URL error occured: {e}")
        raise
    except Exception as e:
        Logger.print_error(f"Download failed! An error occured: {e}")
        raise


def download_progress(block_num, block_size, total_size) -> None:
    """
    Reporthook method for urllib.request.urlretrieve() method call in download_file() |
    :param block_num:
    :param block_size:
    :param total_size: total filesize in bytes
    :return: None
    """
    downloaded = block_num * block_size
    percent = 100 if downloaded >= total_size else downloaded / total_size * 100
    mb = 1024 * 1024
    progress = int(percent / 5)
    remaining = "-" * (20 - progress)
    dl = f"\rDownloading: [{'#' * progress}{remaining}]{percent:.2f}% ({downloaded / mb:.2f}/{total_size / mb:.2f}MB)"
    sys.stdout.write(dl)
    sys.stdout.flush()


def set_nginx_permissions() -> None:
    """
    Check if permissions of the users home directory
    grant execution rights to group and other and set them if not set.
    Required permissions for NGINX to be able to serve Mainsail/Fluidd.
    This seems to have become necessary with Ubuntu 21+. |
    :return: None
    """
    cmd = f"ls -ld {Path.home()} | cut -d' ' -f1"
    homedir_perm = run(cmd, shell=True, stdout=PIPE, text=True)
    permissions = homedir_perm.stdout

    if permissions.count("x") < 3:
        Logger.print_status("Granting NGINX the required permissions ...")
        run(["chmod", "og+x", Path.home()])
        Logger.print_ok("Permissions granted.")


def cmd_sysctl_service(name: str, action: SysCtlServiceAction) -> None:
    """
    Helper method to execute several actions for a specific systemd service. |
    :param name: the service name
    :param action: Either "start", "stop", "restart" or "disable"
    :return: None
    """
    try:
        Logger.print_status(f"{action.capitalize()} {name} ...")
        run(["sudo", "systemctl", action, name], stderr=PIPE, check=True)
        Logger.print_ok("OK!")
    except CalledProcessError as e:
        log = f"Failed to {action} {name}: {e.stderr.decode()}"
        Logger.print_error(log)
        raise


def cmd_sysctl_manage(action: SysCtlManageAction) -> None:
    try:
        run(["sudo", "systemctl", action], stderr=PIPE, check=True)
    except CalledProcessError as e:
        log = f"Failed to run {action}: {e.stderr.decode()}"
        Logger.print_error(log)
        raise


def unit_file_exists(
    name: str, suffix: Literal["service", "timer"], exclude: List[str] | None = None
) -> bool:
    """
    Checks if a systemd unit file of the provided suffix exists.
    :param name: the name of the unit file
    :param suffix: suffix of the unit file, either "service" or "timer"
    :param exclude: List of strings of names to exclude
    :return: True if the unit file exists, False otherwise
    """
    exclude = exclude or []
    pattern = re.compile(f"^{name}(-[0-9a-zA-Z]+)?.{suffix}$")
    service_list = [
        Path(SYSTEMD, service)
        for service in SYSTEMD.iterdir()
        if pattern.search(service.name) and not any(s in service.name for s in exclude)
    ]
    return any(service_list)


def log_process(process: Popen) -> None:
    """
    Helper method to print stdout of a process in near realtime to the console.
    :param process: Process to log the output from
    :return: None
    """
    while True:
        if process.stdout is not None:
            reads = [process.stdout.fileno()]
            ret = select.select(reads, [], [])
            for fd in ret[0]:
                if fd == process.stdout.fileno():
                    line = process.stdout.readline()
                    if line:
                        print(line.strip(), flush=True)
                    else:
                        break

        if process.poll() is not None:
            break


def create_service_file(name: str, content: str) -> None:
    """
    Creates a service file at the provided path with the provided content.
    :param name: the name of the service file
    :param content: the content of the service file
    :return: None
    """
    try:
        run(
            ["sudo", "tee", SYSTEMD.joinpath(name)],
            input=content.encode(),
            stdout=DEVNULL,
            check=True,
        )
        Logger.print_ok(f"Service file created: {SYSTEMD.joinpath(name)}")
    except CalledProcessError as e:
        Logger.print_error(f"Error creating service file: {e}")
        raise


def create_env_file(path: Path, content: str) -> None:
    """
    Creates an env file at the provided path with the provided content.
    :param path: the path of the env file
    :param content: the content of the env file
    :return: None
    """
    try:
        with open(path, "w") as env_file:
            env_file.write(content)
        Logger.print_ok(f"Env file created: {path}")
    except OSError as e:
        Logger.print_error(f"Error creating env file: {e}")
        raise


def remove_system_service(service_name: str) -> None:
    """
    Disables and removes a systemd service
    :param service_name: name of the service unit file - must end with '.service'
    :return: None
    """
    try:
        if not service_name.endswith(".service"):
            raise ValueError(f"service_name '{service_name}' must end with '.service'")

        file: Path = SYSTEMD.joinpath(service_name)
        if not file.exists() or not file.is_file():
            Logger.print_info(f"Service '{service_name}' does not exist! Skipped ...")
            return

        Logger.print_status(f"Removing {service_name} ...")
        cmd_sysctl_service(service_name, "stop")
        cmd_sysctl_service(service_name, "disable")
        remove_with_sudo(file)
        cmd_sysctl_manage("daemon-reload")
        cmd_sysctl_manage("reset-failed")
        Logger.print_ok(f"{service_name} successfully removed!")
    except Exception as e:
        Logger.print_error(f"Error removing {service_name}: {e}")
        raise


def get_service_file_path(instance_type: type, suffix: str) -> Path:
    from utils.common import convert_camelcase_to_kebabcase

    if not isinstance(instance_type, type):
        raise ValueError("instance_type must be a class")

    name: str = convert_camelcase_to_kebabcase(instance_type.__name__)
    if suffix != "":
        name += f"-{suffix}"

    file_path: Path = SYSTEMD.joinpath(f"{name}.service")

    return file_path


def get_distro_info() -> Tuple[str, str]:
    distro_info: str = check_output(["cat", "/etc/os-release"]).decode().strip()

    if not distro_info:
        raise ValueError("Error reading distro info!")

    distro_id: str = ""
    distro_id_like: str = ""
    distro_version: str = ""

    for line in distro_info.split("\n"):
        if line.startswith("ID="):
            distro_id = line.split("=")[1].strip('"').strip()
        if line.startswith("ID_LIKE="):
            distro_id_like = line.split("=")[1].strip('"').strip()
        if line.startswith("VERSION_ID="):
            distro_version = line.split("=")[1].strip('"').strip()

    if distro_id == "raspbian":
        distro_id = distro_id_like

    if not distro_id:
        raise ValueError("Error reading distro id!")
    if not distro_version:
        raise ValueError("Error reading distro version!")

    return distro_id.lower(), distro_version


def get_system_timezone() -> str:
    timezone = "UTC"
    try:
        with open("/etc/timezone", "r") as f:
            timezone = f.read().strip()
    except FileNotFoundError:
        # fallback to reading timezone from timedatectl
        try:
            result = run(
                ["timedatectl", "show", "--property=Timezone"],
                capture_output=True,
                text=True,
                check=True,
            )
            timezone = result.stdout.strip().split("=")[1]
        except CalledProcessError:
            # fallback if timedatectl fails, try reading from readlink
            try:
                result = run(
                    ["readlink", "-f", "/etc/localtime"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                timezone = result.stdout.strip().split("zoneinfo/")[1]
            except (CalledProcessError, IndexError):
                Logger.print_warn("Could not determine system timezone, using UTC")
    return timezone

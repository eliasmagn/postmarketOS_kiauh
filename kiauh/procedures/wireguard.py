# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run

from core.logger import DialogType, Logger
from core.types.color import Color
from utils.common import check_install_dependencies
from utils.input_utils import get_confirm, get_string_input
from utils.sys_utils import InitSystem, cmd_sysctl_service, get_init_system

WIREGUARD_DIR = Path("/etc/wireguard")


def provision_wireguard() -> None:
    """Install WireGuard tooling and guide the user through a client setup."""

    Logger.print_dialog(
        DialogType.CUSTOM,
        [
            "WireGuard provides an encrypted tunnel so you can reach Moonraker and",
            "web UIs securely without exposing them to the public internet.",
            "\n\n",
            "KIAUH can install the required tools, help you generate a key pair,",
            "and write a client configuration under /etc/wireguard.",
            "You will need the tunnel address assigned to this device, the",
            "server's public key, endpoint (host:port), and the list of networks",
            "the tunnel should reach.",
        ],
        custom_title="WireGuard provisioning",
        custom_color=Color.CYAN,
    )

    if not get_confirm(
        "Install WireGuard tooling and configure a client now?", default_choice=False
    ):
        Logger.print_info("Skipping WireGuard provisioning at user request.")
        return

    check_install_dependencies({"wireguard-tools"}, include_global=False)

    interface = get_string_input(
        "WireGuard interface name", regex=r"^[a-zA-Z0-9_.-]+$", default="wg0"
    )

    private_key, public_key = _obtain_keypair()
    Logger.print_info(
        "Share this device's WireGuard public key with your VPN gateway:"
    )
    Logger.print_status(public_key)

    tunnel_address = get_string_input(
        "Client tunnel address (CIDR, e.g. 10.42.0.2/32)", allow_special_chars=True
    )
    dns_servers = get_string_input(
        "DNS servers for the tunnel (comma separated, optional)",
        allow_special_chars=True,
        allow_empty=True,
        default="",
    )
    peer_public_key = get_string_input(
        "Remote peer public key", allow_special_chars=True
    )
    preshared_key = get_string_input(
        "Pre-shared key (optional)",
        allow_special_chars=True,
        allow_empty=True,
        default="",
    )
    allowed_ips = get_string_input(
        "Allowed IPs for the peer",
        allow_special_chars=True,
        default="0.0.0.0/0, ::/0",
    )
    endpoint = get_string_input(
        "Peer endpoint (host:port)", allow_special_chars=True
    )
    keepalive = get_string_input(
        "Persistent keepalive (seconds, optional)",
        allow_special_chars=True,
        allow_empty=True,
        default="25",
    )

    config_path = WIREGUARD_DIR.joinpath(f"{interface}.conf")
    _ensure_wireguard_directory()
    _backup_existing_config(config_path)
    _write_wireguard_config(
        config_path,
        interface,
        private_key,
        tunnel_address,
        dns_servers,
        peer_public_key,
        preshared_key,
        allowed_ips,
        endpoint,
        keepalive,
    )
    _set_config_permissions(config_path)
    _enable_wireguard_service(interface)

    Logger.print_ok(
        "WireGuard provisioning complete. Use 'wg show' to inspect tunnel status.",
        end="\n\n",
    )


def _obtain_keypair() -> tuple[str, str]:
    if get_confirm("Generate a new WireGuard key pair?", default_choice=True):
        try:
            private_key, public_key = _generate_keypair()
            Logger.print_ok("Generated WireGuard key pair.")
            return private_key, public_key
        except CalledProcessError as error:
            Logger.print_warn(
                "Automatic key generation failed. Please supply keys manually."
            )
            Logger.print_error(str(error))

    private_key = get_string_input(
        "Enter existing WireGuard private key", allow_special_chars=True
    )
    public_key = get_string_input(
        "Corresponding public key (leave blank to derive)",
        allow_special_chars=True,
        allow_empty=True,
        default="",
    )
    if not public_key:
        try:
            public_key = _derive_public_key(private_key)
            Logger.print_ok("Derived public key from the provided private key.")
        except CalledProcessError as error:
            Logger.print_warn(
                "Failed to derive the public key. Please paste it manually."
            )
            Logger.print_error(str(error))
            public_key = get_string_input(
                "Remote view of this peer's public key",
                allow_special_chars=True,
            )
    return private_key, public_key


def _generate_keypair() -> tuple[str, str]:
    result = run(["wg", "genkey"], stdout=PIPE, stderr=PIPE, text=True, check=True)
    private_key = result.stdout.strip()
    if not private_key:
        raise CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    public_result = run(
        ["wg", "pubkey"],
        input=f"{private_key}\n",
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        check=True,
    )
    public_key = public_result.stdout.strip()
    if not public_key:
        raise CalledProcessError(
            public_result.returncode,
            public_result.args,
            public_result.stdout,
            public_result.stderr,
        )
    return private_key, public_key


def _derive_public_key(private_key: str) -> str:
    result = run(
        ["wg", "pubkey"],
        input=f"{private_key}\n",
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        check=True,
    )
    public_key = result.stdout.strip()
    if not public_key:
        raise CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return public_key


def _ensure_wireguard_directory() -> None:
    try:
        run(["sudo", "mkdir", "-p", WIREGUARD_DIR.as_posix()], check=True)
    except CalledProcessError as error:
        Logger.print_error(f"Failed to create {WIREGUARD_DIR}: {error}")
        raise


def _backup_existing_config(config_path: Path) -> None:
    if not config_path.exists():
        return
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_suffix(config_path.suffix + f".{timestamp}.bak")
    try:
        Logger.print_status(f"Backing up existing configuration to {backup_path} ...")
        run(
            [
                "sudo",
                "cp",
                config_path.as_posix(),
                backup_path.as_posix(),
            ],
            check=True,
        )
        Logger.print_ok("Backup complete.")
    except CalledProcessError as error:
        Logger.print_error(f"Failed to backup existing config: {error}")
        raise


def _write_wireguard_config(
    config_path: Path,
    interface: str,
    private_key: str,
    tunnel_address: str,
    dns_servers: str,
    peer_public_key: str,
    preshared_key: str,
    allowed_ips: str,
    endpoint: str,
    keepalive: str,
) -> None:
    lines = [
        "[Interface]",
        f"PrivateKey = {private_key}",
        f"Address = {tunnel_address}",
    ]
    if dns_servers:
        lines.append(f"DNS = {dns_servers}")

    lines.extend(
        [
            "",
            "[Peer]",
            f"PublicKey = {peer_public_key}",
        ]
    )

    if preshared_key:
        lines.append(f"PresharedKey = {preshared_key}")

    if allowed_ips:
        lines.append(f"AllowedIPs = {allowed_ips}")

    lines.append(f"Endpoint = {endpoint}")

    if keepalive:
        lines.append(f"PersistentKeepalive = {keepalive}")

    content = "\n".join(lines) + "\n"

    try:
        Logger.print_status(
            f"Writing WireGuard configuration for '{interface}' to {config_path} ..."
        )
        run(
            ["sudo", "tee", config_path.as_posix()],
            input=content.encode(),
            stdout=PIPE,
            stderr=PIPE,
            check=True,
        )
        Logger.print_ok("Configuration written.")
    except CalledProcessError as error:
        Logger.print_error(f"Failed to write WireGuard configuration: {error}")
        raise


def _set_config_permissions(config_path: Path) -> None:
    try:
        Logger.print_status("Setting strict permissions on the WireGuard config ...")
        run(["sudo", "chmod", "600", config_path.as_posix()], check=True)
        Logger.print_ok("Permissions updated.")
    except CalledProcessError as error:
        Logger.print_error(f"Failed to set permissions on {config_path}: {error}")
        raise


def _enable_wireguard_service(interface: str) -> None:
    init_system = get_init_system()
    service_name: str | None
    if init_system == InitSystem.OPENRC:
        service_name = f"wg-quick.{interface}"
    elif init_system == InitSystem.SYSTEMD:
        service_name = f"wg-quick@{interface}"
    else:
        service_name = None

    if service_name is None:
        Logger.print_warn(
            "Unsupported init system detected. Enable the WireGuard tunnel manually."
        )
        return

    try:
        cmd_sysctl_service(service_name, "enable")
    except CalledProcessError:
        Logger.print_warn(
            "Failed to enable automatic WireGuard startup. Enable it manually if desired."
        )

    try:
        cmd_sysctl_service(service_name, "start")
    except CalledProcessError:
        Logger.print_warn(
            "WireGuard tunnel could not be started automatically. Validate the configuration and start it manually."
        )

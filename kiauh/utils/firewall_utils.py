# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import ipaddress
import shutil
from subprocess import PIPE, CalledProcessError, run
from typing import Dict, Iterable, List, Optional

from core.logger import DialogType, Logger
from core.types.color import Color
from utils.input_utils import (
    get_confirm,
    get_selection_input,
    get_string_input,
)


NFT_CHAIN_CMD = ["sudo", "nft", "list", "chain", "inet", "filter", "input"]
NFT_ADD_RULE_CMD = ["sudo", "nft", "add", "rule", "inet", "filter", "input"]


def configure_nftables(service_name: str, ports: Iterable[int], context: str | None = None) -> None:
    """Prompt the user to open nftables ports for a service."""

    unique_ports = sorted({int(p) for p in ports if p})
    if not unique_ports:
        return

    if not shutil.which("nft"):
        Logger.print_info(
            "nftables binary not found. Skipping firewall configuration prompt."
        )
        return

    chain_state = _list_input_chain()
    if chain_state is None:
        Logger.print_warn(
            "Unable to inspect the default nftables input chain. Please adjust your "
            "firewall rules manually if needed."
        )
        return

    missing_ports = [p for p in unique_ports if not _has_rule_for_port(chain_state, p)]
    if not missing_ports:
        Logger.print_info(
            f"Existing nftables rules already allow access to {service_name} on "
            f"the configured ports."
        )
        return

    description = (
        f"nftables rules are required for {service_name}."
        if context is None
        else context
    )
    Logger.print_dialog(
        DialogType.CUSTOM,
        custom_title=f"Configure nftables for {service_name}",
        custom_color=Color.CYAN,
        content=[
            description,
            "\n\n",
            "KIAUH can automatically add nftables allow rules for the following ports:",
            ", ".join(str(p) for p in missing_ports),
            "\n\n",
            "The rules can be scoped to all networks, detected local subnets, or a",
            "custom list of networks/hosts (CIDR notation).",
        ],
    )

    if not get_confirm(
        f"Add nftables rules for {service_name}?", default_choice=True
    ):
        Logger.print_info(
            f"Skipping nftables configuration for {service_name} at user request."
        )
        return

    networks = _select_network_scope(service_name)
    if networks is None:
        Logger.print_info(
            f"No network scope selected. Skipping nftables configuration for {service_name}."
        )
        return

    _apply_nft_rules(service_name, missing_ports, networks)


def _select_network_scope(service_name: str) -> Optional[Dict[str, List[str]]]:
    options = {
        "1": "Allow access from all networks",
        "2": "Allow access from detected local network(s)",
        "3": "Enter a custom list of networks or host addresses",
    }

    Logger.print_dialog(
        DialogType.CUSTOM,
        custom_title="nftables access scope",
        custom_color=Color.CYAN,
        content=[
            "Choose how broadly the new rule(s) should allow incoming connections.",
            "Option 2 inspects active network interfaces and proposes their subnet",
            "prefixes. Option 3 accepts a comma-separated list of CIDR blocks or",
            "individual IP addresses (IPv4/IPv6).",
        ],
    )

    detected_networks = _detect_local_networks()
    has_detected = any(detected_networks.values())
    default_option = "2" if has_detected else "1"
    selection = get_selection_input(
        "Select nftables access scope", options, default=default_option
    )

    if selection == "1":
        return {"ip": ["0.0.0.0/0"], "ip6": ["::/0"]}

    if selection == "2":
        if not has_detected:
            Logger.print_warn(
                "No local networks detected automatically. Falling back to an allow-all rule."
            )
            return {"ip": ["0.0.0.0/0"], "ip6": ["::/0"]}
        return detected_networks

    return _prompt_custom_networks(service_name)


def _prompt_custom_networks(service_name: str) -> Optional[Dict[str, List[str]]]:
    while True:
        value = get_string_input(
            "Enter networks/hosts (comma-separated CIDR, e.g. 192.168.1.0/24,fd00::/8)",
            allow_special_chars=True,
        ).strip()

        entries = [v.strip() for v in value.split(",") if v.strip()]
        if not entries:
            Logger.print_error("Input must not be empty!")
            continue

        networks: Dict[str, List[str]] = {"ip": [], "ip6": []}
        try:
            for entry in entries:
                network = ipaddress.ip_network(entry, strict=False)
                key = "ip6" if network.version == 6 else "ip"
                formatted = str(network)
                if formatted not in networks[key]:
                    networks[key].append(formatted)
        except ValueError:
            Logger.print_error(
                "One or more entries were invalid. Please provide CIDR notation or single IPs."
            )
            continue

        if not networks["ip"] and not networks["ip6"]:
            Logger.print_error("No valid networks provided. Try again.")
            continue

        Logger.print_info(
            f"Configuring nftables rules for {service_name} with the provided networks."
        )
        return networks


def _detect_local_networks() -> Dict[str, List[str]]:
    detected: Dict[str, List[str]] = {"ip": [], "ip6": []}

    commands = [
        ("ip", ["ip", "-o", "-f", "inet", "addr", "show"]),
        ("ip6", ["ip", "-o", "-f", "inet6", "addr", "show"]),
    ]

    for family, command in commands:
        try:
            result = run(command, stdout=PIPE, stderr=PIPE, text=True, check=True)
        except (CalledProcessError, FileNotFoundError):
            continue

        for line in result.stdout.splitlines():
            if " lo " in line or "scope host" in line:
                continue
            if family == "ip6" and " scope link " in line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            address = parts[3]
            try:
                network = ipaddress.ip_network(address, strict=False)
            except ValueError:
                continue
            key = "ip6" if network.version == 6 else "ip"
            formatted = str(network)
            if formatted not in detected[key]:
                detected[key].append(formatted)

    return detected


def _apply_nft_rules(
    service_name: str, ports: Iterable[int], networks: Dict[str, List[str]]
) -> None:
    chain_state = _list_input_chain()
    if chain_state is None:
        Logger.print_warn(
            "Unable to re-read nftables chain. Skipping automatic rule creation."
        )
        return

    for port in ports:
        if not networks["ip"] and not networks["ip6"]:
            _add_rule(service_name, port, None, chain_state)
            chain_state = _list_input_chain() or chain_state
            continue

        for family in ("ip", "ip6"):
            for network in networks[family]:
                _add_rule(service_name, port, (family, network), chain_state)
                chain_state = _list_input_chain() or chain_state


def _add_rule(
    service_name: str,
    port: int,
    scope: Optional[tuple[str, str]],
    chain_state: str,
) -> None:
    family_label = "" if scope is None else f" {scope[0]} saddr {scope[1]}"
    search_term = f"tcp dport {port}"
    if scope is not None:
        search_term = f"{scope[0]} saddr {scope[1]} {search_term}"

    if search_term in chain_state:
        return

    Logger.print_status(
        f"Adding nftables rule for {service_name} on port {port}{family_label}."
    )

    command = list(NFT_ADD_RULE_CMD)
    if scope is not None:
        family, network = scope
        command.extend([family, "saddr", network])
    command.extend(["tcp", "dport", str(port), "accept"])

    try:
        run(command, stderr=PIPE, check=True)
    except CalledProcessError as exc:
        Logger.print_error(
            "Failed to add nftables rule: "
            f"{exc.stderr.decode(errors='ignore').strip()}"
        )
    else:
        Logger.print_ok(
            f"nftables now allows {service_name} on port {port}{family_label}."
        )


def _list_input_chain() -> Optional[str]:
    try:
        result = run(NFT_CHAIN_CMD, stdout=PIPE, stderr=PIPE, text=True, check=True)
        return result.stdout
    except CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        Logger.print_warn(
            "Could not inspect nftables input chain: "
            f"{stderr}"
        )
        Logger.print_warn(
            "Unable to inspect the default nftables input chain. "
            "Please adjust your firewall rules manually if needed."
        )
        if "No such file or directory" in stderr or "does not exist" in stderr:
            Logger.print_info(
                "The default nftables filter/input chain is missing. "
                "Refer to https://wiki.postmarketos.org/wiki/Firewall for manual "
                "configuration guidance."
            )
    except FileNotFoundError:
        Logger.print_warn("nft command not available on this system.")
    return None


def _has_rule_for_port(chain_state: str, port: int) -> bool:
    pattern = f"tcp dport {port}"
    return any(pattern in line for line in chain_state.splitlines())

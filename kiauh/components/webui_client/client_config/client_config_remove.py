# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #


import shlex
from pathlib import Path
from typing import List, Optional

from components.klipper.klipper import Klipper
from components.moonraker.moonraker import Moonraker
from components.webui_client.base_data import BaseWebClientConfig
from core.logger import Logger
from core.services.backup_service import BackupService
from core.services.message_service import Message
from core.types.color import Color
from utils.config_utils import remove_config_section
from utils.fs_utils import run_remove_routines
from utils.instance_type import InstanceType
from utils.instance_utils import get_instances


def run_client_config_removal(
    client_config: BaseWebClientConfig,
    kl_instances: List[Klipper],
    mr_instances: List[Moonraker],
) -> Message:
    completion_msg = Message(
        title=f"{client_config.display_name} Removal Process completed",
        color=Color.GREEN,
    )
    Logger.print_status(f"Removing {client_config.display_name} ...")

    completion_msg = remove_cfg_symlink(
        client_config, completion_msg, kl_instances
    )
    if run_remove_routines(client_config.config_dir):
        completion_msg.text.append(f"● {client_config.display_name} removed")

    BackupService().backup_printer_config_dir()

    completion_msg = remove_moonraker_config_section(
        completion_msg, client_config, mr_instances
    )

    completion_msg = remove_printer_config_section(
        completion_msg, client_config, kl_instances
    )

    if completion_msg.text:
        completion_msg.text.insert(0, "The following actions were performed:")
    else:
        completion_msg.color = Color.YELLOW
        completion_msg.centered = True
        completion_msg.text = ["Nothing to remove."]

    return completion_msg


def remove_cfg_symlink(
    client_config: BaseWebClientConfig,
    message: Message,
    kl_instances: Optional[List[Klipper]] = None,
) -> Message:
    instances: List[Klipper] = kl_instances or get_instances(Klipper)
    removed_from: List[Klipper] = []
    for instance in instances:
        cfg = instance.base.cfg_dir.joinpath(client_config.config_filename)
        if run_remove_routines(cfg):
            removed_from.append(instance)
    text = f"{client_config.display_name} removed from instance"
    return update_msg(removed_from, message, text)


def remove_printer_config_section(
    message: Message, client_config: BaseWebClientConfig, kl_instances: List[Klipper]
) -> Message:
    kl_section = client_config.config_section
    removed_sections = remove_config_section(kl_section, kl_instances)
    text = f"Klipper config section '{kl_section}' removed for instance"
    message = update_msg(removed_sections, message, text)

    disabled_includes = disable_plain_include(
        client_config.config_filename, kl_instances
    )
    text = (
        f"Inline include for '{client_config.config_filename}' disabled in instance"
    )
    return update_msg(disabled_includes, message, text)


def disable_plain_include(
    filename: str, instances: List[Klipper]
) -> List[Klipper]:
    affected: List[Klipper] = []
    for instance in instances:
        cfg_file = instance.cfg_file
        if not cfg_file.exists():
            Logger.print_warn(f"'{cfg_file}' not found!")
            continue

        try:
            lines = cfg_file.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as e:
            Logger.print_error(f"Unable to read '{cfg_file}':\n{e}")
            continue

        changed = False
        updated: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                updated.append(line)
                continue

            try:
                tokens = shlex.split(stripped, comments=True, posix=True)
            except ValueError:
                updated.append(line)
                continue

            if len(tokens) < 2 or tokens[0].lower() != "include":
                updated.append(line)
                continue

            include_target = Path(tokens[1]).name
            if include_target != filename:
                updated.append(line)
                continue

            leading = line[: len(line) - len(line.lstrip())]
            body = line.lstrip().rstrip("\n")
            newline = "\n" if line.endswith("\n") else ""
            updated.append(
                f"{leading}# {body}  # disabled by KIAUH{newline}"
            )
            changed = True

        if not changed:
            continue

        Logger.print_status(
            f"Disable inline include '{filename}' in '{cfg_file}' ..."
        )
        try:
            cfg_file.write_text("".join(updated), encoding="utf-8")
        except OSError as e:
            Logger.print_error(f"Unable to update '{cfg_file}':\n{e}")
            continue
        Logger.print_ok("OK!")
        affected.append(instance)

    return affected


def remove_moonraker_config_section(
    message: Message, client_config: BaseWebClientConfig, mr_instances: List[Moonraker]
) -> Message:
    mr_section = f"update_manager {client_config.name}"
    mr_instances = remove_config_section(mr_section, mr_instances)
    text = f"Moonraker config section '{mr_section}' removed for instance"
    return update_msg(mr_instances, message, text)


def update_msg(instances: List[InstanceType], message: Message, text: str) -> Message:
    if not instances:
        return message

    instance_names = [i.service_file_path.stem for i in instances]
    message.text.append(f"● {text}: {', '.join(instance_names)}")
    return message

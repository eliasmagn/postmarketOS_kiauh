#!/usr/bin/env python3
"""Provide apt-compatible command wrappers backed by apk for Moonraker."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Sequence


class CommandError(Exception):
    """Raised when an unsupported command is requested."""


def _ensure_apk() -> str:
    apk = shutil.which("apk")
    if not apk:
        raise FileNotFoundError("apk executable not found in PATH")
    return apk


def _run_apk(args: Sequence[str]) -> int:
    apk = _ensure_apk()
    env = os.environ.copy()
    env.pop("DEBIAN_FRONTEND", None)
    result = subprocess.run([apk, *args])
    return result.returncode


def _parse_subcommand(args: List[str]) -> tuple[str | None, List[str]]:
    subcommand: str | None = None
    remainder: List[str] = []
    for arg in args:
        if subcommand is None and arg.startswith("-"):
            continue
        if subcommand is None:
            subcommand = arg
            continue
        remainder.append(arg)
    return subcommand, remainder


def _filter_packages(args: Iterable[str]) -> List[str]:
    return [arg for arg in args if not arg.startswith("-")]


def _apt_list_upgradable() -> int:
    apk = _ensure_apk()
    output = subprocess.run([apk, "list", "-u"], capture_output=True, text=True)
    if output.returncode != 0:
        sys.stderr.write(output.stderr)
        return output.returncode

    lines = [line.strip() for line in output.stdout.splitlines() if line.strip()]
    print("Listing...")
    print("Done")
    pkg_regex = re.compile(
        r"^(?P<name>.+?)-(?P<oldver>\d[^\s]*)\s+available\s+\((?P<newver>[^)]+)\)"
    )
    for line in lines:
        match = pkg_regex.match(line)
        if not match:
            continue
        name = match.group("name")
        old_version = match.group("oldver")
        new_version = match.group("newver")
        print(f"{name}/apk {new_version} [upgradable from: {old_version}]")
    return 0


def _apt_cache_search(args: List[str]) -> int:
    if not args:
        raise CommandError("missing search arguments")

    if args[0] != "--names-only":
        raise CommandError("only --names-only searches are supported")

    if len(args) < 2:
        raise CommandError("missing search pattern")

    pattern = args[1]
    pattern = pattern.strip("'\"")
    names = [token.strip("^") for token in pattern.split("|") if token]
    names = [name.strip("$") for name in names]

    apk = _ensure_apk()
    for name in names:
        result = subprocess.run([apk, "search", "-e", name], capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip():
            continue
        first_line = result.stdout.splitlines()[0].strip()
        pkg_name = first_line.split()[0].rsplit("-", 2)[0]
        print(f"{pkg_name} - apk package")
    return 0


def handle_apt_command(args: List[str]) -> int:
    subcommand, remainder = _parse_subcommand(args)
    if subcommand == "list" and remainder == ["--upgradable"]:
        return _apt_list_upgradable()
    raise CommandError(f"unsupported apt command: {' '.join(args)}")


def handle_apt_get_command(args: List[str]) -> int:
    subcommand, remainder = _parse_subcommand(args)
    packages = _filter_packages(remainder)

    if subcommand == "update":
        return _run_apk(["update"])
    if subcommand == "upgrade":
        return _run_apk(["upgrade"])
    if subcommand == "install":
        if not packages:
            raise CommandError("no packages provided to install")
        return _run_apk(["add", "--upgrade", *packages])
    raise CommandError(f"unsupported apt-get command: {' '.join(args)}")


def handle_apt_cache_command(args: List[str]) -> int:
    subcommand, remainder = _parse_subcommand(args)
    if subcommand != "search":
        raise CommandError(f"unsupported apt-cache command: {' '.join(args)}")
    return _apt_cache_search(remainder)


def main() -> int:
    command = Path(sys.argv[0]).name
    args = sys.argv[1:]

    try:
        if command in {"apt", "apt-cli"}:
            return handle_apt_command(args)
        if command == "apt-get":
            return handle_apt_get_command(args)
        if command == "apt-cache":
            return handle_apt_cache_command(args)
        raise CommandError(f"unsupported command wrapper: {command}")
    except CommandError as exc:
        sys.stderr.write(f"apk-apt-wrapper: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"apk-apt-wrapper: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

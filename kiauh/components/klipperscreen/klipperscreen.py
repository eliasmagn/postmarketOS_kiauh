# ======================================================================= #
#  Copyright (C) 2020 - 2025 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
import os
import re
import shutil
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from subprocess import CalledProcessError, run
from textwrap import dedent
from typing import Dict, List, Optional

from components.klipper.klipper import Klipper
from components.klipperscreen import (
    KLIPPERSCREEN_DIR,
    KLIPPERSCREEN_ENV_DIR,
    KLIPPERSCREEN_INSTALL_SCRIPT,
    KLIPPERSCREEN_INSTALL_SCRIPT_ASSET,
    KLIPPERSCREEN_LOG_NAME,
    KLIPPERSCREEN_REPO,
    KLIPPERSCREEN_REQ_FILE,
    KLIPPERSCREEN_SERVICE_FILE,
    KLIPPERSCREEN_SERVICE_NAME,
    KLIPPERSCREEN_UPDATER_SECTION_NAME,
)
from components.moonraker.moonraker import Moonraker
from core.instance_manager.instance_manager import InstanceManager
from core.logger import DialogType, Logger
from core.services.backup_service import BackupService
from core.settings.kiauh_settings import KiauhSettings
from core.types.component_status import ComponentStatus
from utils.common import (
    check_install_dependencies,
    get_install_status,
)
from utils.config_utils import add_config_section, remove_config_section
from utils.fs_utils import remove_with_sudo
from utils.git_utils import (
    git_clone_wrapper,
    git_pull_wrapper,
)
from utils.input_utils import get_confirm, get_selection_input
from utils.instance_utils import get_instances
from utils.sys_utils import (
    InitSystem,
    PackageManager,
    check_python_version,
    cmd_sysctl_service,
    detect_init_system,
    get_service_directory,
    get_package_manager,
    install_python_requirements,
    remove_system_service,
)


@dataclass(frozen=True)
class WaylandPreset:
    key: str
    name: str
    desktop: str
    description: str
    env: Dict[str, str]
    notes: List[str]


class AutostartBackend(Enum):
    NONE = auto()
    SYSTEMD_USER = auto()
    OPENRC = auto()


@dataclass
class AutostartResult:
    preset: WaylandPreset
    wrapper_path: Path
    desktop_entry: Path
    backend: AutostartBackend = AutostartBackend.NONE
    backend_path: Optional[Path] = None
    autostart_entry: Optional[Path] = None
    login_snippet: Optional[Path] = None
    profile_injection: Optional[Path] = None

    @property
    def uses_user_autostart(self) -> bool:
        return self.backend is not AutostartBackend.NONE or self.login_snippet is not None


@dataclass
class DisplayInfo:
    name: str
    width: int
    height: int
    rotation: Optional[int] = None


WAYLAND_PRESETS: Dict[str, WaylandPreset] = {
    "1": WaylandPreset(
        key="1",
        name="Phosh",
        desktop="Phosh",
        description=(
            "Optimised for GNOME/Phosh shells where GTK, Qt and SDL apps need explicit "
            "Wayland configuration and where fractional scaling is handled by the shell."
        ),
        env={
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-0",
            "QT_QPA_PLATFORM": "wayland",
            "QT_WAYLAND_DISABLE_WINDOWDECORATION": "1",
            "GDK_BACKEND": "wayland",
            "SDL_VIDEODRIVER": "wayland",
            "MOZ_ENABLE_WAYLAND": "1",
            "CLUTTER_BACKEND": "wayland",
            "WLR_NO_HARDWARE_CURSORS": "1",
        },
        notes=[
            "Makes KlipperScreen follow Phosh's compositor scaling.",
            "Disables Qt's client-side decorations to avoid double title bars.",
        ],
    ),
    "2": WaylandPreset(
        key="2",
        name="Plasma Mobile",
        desktop="Plasma Mobile",
        description=(
            "Targets Plasma Mobile sessions that ship the KDE Wayland compositor and "
            "QtQuick stack. Applies KDE-specific hints alongside generic Wayland flags."
        ),
        env={
            "XDG_SESSION_TYPE": "wayland",
            "QT_QPA_PLATFORM": "wayland",
            "QT_WAYLAND_DISABLE_WINDOWDECORATION": "1",
            "GDK_BACKEND": "wayland",
            "SDL_VIDEODRIVER": "wayland",
            "MOZ_ENABLE_WAYLAND": "1",
            "QT_QUICK_CONTROLS_STYLE": "Plasma",
            "QT_QPA_PLATFORMTHEME": "kde",
            "KWIN_DRM_USE_MODIFIERS": "1",
            "XCURSOR_SIZE": "24",
        },
        notes=[
            "Uses KDE's platform theme so widgets inherit Plasma styling.",
            "Keeps cursor size predictable when Plasma's scaling kicks in.",
        ],
    ),
    "3": WaylandPreset(
        key="3",
        name="Sxmo",
        desktop="Sxmo",
        description=(
            "Targets Sxmo's wlroots session defaults so KlipperScreen launches under its "
            "dwl/sway based environments on Qualcomm handsets. Applies the wlroots "
            "compatibility flags typically exported by sxmo-utils."
        ),
        env={
            "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "sxmo",
            "XDG_SESSION_DESKTOP": "sxmo",
            "WAYLAND_DISPLAY": "wayland-0",
            "QT_QPA_PLATFORM": "wayland-egl",
            "QT_WAYLAND_DISABLE_WINDOWDECORATION": "1",
            "GDK_BACKEND": "wayland,x11",
            "SDL_VIDEODRIVER": "wayland",
            "MOZ_ENABLE_WAYLAND": "1",
            "CLUTTER_BACKEND": "wayland",
            "WLR_RENDERER_ALLOW_SOFTWARE": "1",
            "WLR_NO_HARDWARE_CURSORS": "1",
            "XCURSOR_SIZE": "32",
        },
        notes=[
            "Mirrors the environment exported by sxmo-utils so wlroots-based shells on "
            "qcom-msm8953 devices can spawn KlipperScreen without extra wrappers.",
            "For systems with working GPU drivers you can drop WLR_RENDERER_ALLOW_SOFTWARE "
            "after verifying hardware acceleration.",
        ],
    ),
}

WAYLAND_PRESET_SKIP_KEY = "0"
KLIPPERSCREEN_CONFIG_PATH = Path.home().joinpath("printer_data/config/KlipperScreen.conf")
BACKEND_TRACK_FILENAME = ".kiauh-backend-choice"


def _sync_installer_script_with_asset() -> None:
    """Ensure the KlipperScreen installer understands apk based systems."""

    if not KLIPPERSCREEN_INSTALL_SCRIPT_ASSET.exists():
        return

    if get_package_manager() is not PackageManager.APK:
        return

    try:
        shutil.copy(KLIPPERSCREEN_INSTALL_SCRIPT_ASSET, KLIPPERSCREEN_INSTALL_SCRIPT)
        os.chmod(KLIPPERSCREEN_INSTALL_SCRIPT, 0o755)
        Logger.print_info(
            "Patched KlipperScreen installer to use apk/doas aware helper script."
        )
    except OSError as err:
        Logger.print_warn(
            "Unable to copy apk-aware KlipperScreen installer override. Falling back "
            f"to upstream script ({err})."
        )


_START_SCRIPT_SENTINEL = "# KIAUH fallback: ensure default client selection"


def _ensure_start_script_client_fallback() -> None:
    """Make the upstream launcher default to KlipperScreen when KS_XCLIENT is unset."""

    script_path = KLIPPERSCREEN_DIR.joinpath("scripts/KlipperScreen-start.sh")
    if not script_path.exists():
        return

    try:
        content = script_path.read_text(encoding="utf-8")
    except OSError:
        return

    if _START_SCRIPT_SENTINEL in content:
        return

    needle = "SCRIPTPATH=$(dirname $(realpath $0))"
    if needle not in content:
        Logger.print_warn(
            "Unable to inject KlipperScreen fallback into KlipperScreen-start.sh "
            "because the expected anchor was not found."
        )
        return

    fallback_block = dedent(
        """
# KIAUH fallback: ensure default client selection
KS_BASEDIR="${SCRIPTPATH%/scripts}"
if [ -z "${KS_DIR:-}" ]; then
    KS_DIR="$KS_BASEDIR"
fi
if [ -z "${KS_ENV:-}" ]; then
    KS_ENV="${HOME}/.KlipperScreen-env"
fi
if [ -z "${KS_XCLIENT:-}" ]; then
    KS_XCLIENT="${KS_ENV}/bin/python ${KS_DIR}/screen.py"
fi
        """
    ).rstrip()

    updated = content.replace(needle, f"{needle}\n{fallback_block}", 1)
    try:
        script_path.write_text(updated, encoding="utf-8")
        Logger.print_info(
            "Injected default KS_XCLIENT fallback into KlipperScreen-start.sh so "
            "manual launches use screen.py even when services skip environment "
            "exports."
        )
    except OSError:
        Logger.print_warn(
            "Failed to update KlipperScreen-start.sh with KS_XCLIENT fallback."
        )


def prompt_wayland_preset() -> Optional[WaylandPreset]:
    Logger.print_info(
        "KlipperScreen now ships Wayland session presets. Select the one that matches your "
        "mobile shell to pre-create launchers with the right environment variables."
    )
    Logger.print_info(
        "If you prefer to handle this manually you can skip the preset and adjust the files "
        "under ~/KlipperScreen/scripts later."
    )

    Logger.print_status("Available presets:")
    Logger.print_info(f"  {WAYLAND_PRESET_SKIP_KEY}) Skip Wayland preset creation")
    for key, preset in WAYLAND_PRESETS.items():
        Logger.print_info(f"  {key}) {preset.name} — {preset.description}")
        for note in preset.notes:
            Logger.print_info(f"       • {note}")

    selection = get_selection_input(
        "Choose a Wayland preset (or 0 to skip)",
        {**WAYLAND_PRESETS, WAYLAND_PRESET_SKIP_KEY: WAYLAND_PRESET_SKIP_KEY},
        default=WAYLAND_PRESET_SKIP_KEY,
    )
    if selection == WAYLAND_PRESET_SKIP_KEY:
        return None
    return WAYLAND_PRESETS[selection]


def configure_wayland_launchers(preset: WaylandPreset) -> AutostartResult:
    try:
        result = _configure_wayland_launchers_internal(preset)
        Logger.print_ok(
            "Wayland launchers created in ~/.local/share/applications."
        )
        if result.backend is AutostartBackend.SYSTEMD_USER and result.backend_path is not None:
            Logger.print_info(
                "Systemd user service stored in ~/.config/systemd/user. Enable it with "
                f"'systemctl --user enable --now {result.backend_path.name}'."
            )
        elif result.backend is AutostartBackend.OPENRC and result.backend_path is not None:
            Logger.print_info(
                "OpenRC user service stub created under ~/.config/openrc/init.d (add it "
                "with rc-update to run automatically)."
            )
        if result.autostart_entry is not None:
            Logger.print_info(
                "Autostart desktop entry written to ~/.config/autostart for the "
                "detected mobile shell."
            )
        if result.login_snippet is not None:
            Logger.print_info(
                "Login shell snippet stored under ~/.config/profile.d to start "
                "KlipperScreen after Moonraker is reachable."
            )
            if result.profile_injection is not None:
                Logger.print_info(
                    f"Ensured {result.profile_injection} sources ~/.config/profile.d/*.sh."
                )
        return result
    except Exception as err:  # pragma: no cover - defensive logging only
        Logger.print_warn(
            "Failed to create Wayland launcher helpers. You can re-run the preset from the "
            "KlipperScreen installer menu."
        )
        Logger.print_error(str(err))
        raise


def _configure_wayland_launchers_internal(preset: WaylandPreset) -> AutostartResult:
    wrapper_path = _write_wayland_wrapper(preset)
    desktop_path = _write_desktop_entry(wrapper_path, preset)
    service_result = _write_user_service(wrapper_path, preset)

    autostart_entry: Optional[Path] = None
    login_snippet: Optional[Path] = None
    profile_injection: Optional[Path] = None

    detected_shell = _detect_mobile_shell()
    if detected_shell and _shell_matches_preset(detected_shell, preset):
        autostart_entry = _write_autostart_entry(wrapper_path, preset, detected_shell)
    elif service_result.backend is AutostartBackend.OPENRC and detected_shell is None:
        login_snippet, profile_injection = _write_login_shell_snippet(wrapper_path, preset)

    return AutostartResult(
        preset=preset,
        wrapper_path=wrapper_path,
        desktop_entry=desktop_path,
        backend=service_result.backend,
        backend_path=service_result.path,
        autostart_entry=autostart_entry,
        login_snippet=login_snippet,
        profile_injection=profile_injection,
    )


def _write_wayland_wrapper(preset: WaylandPreset) -> Path:
    bin_dir = Path.home().joinpath(".local/bin")
    bin_dir.mkdir(parents=True, exist_ok=True)
    wrapper_path = bin_dir.joinpath(
        f"klipperscreen-{preset.name.lower().replace(' ', '-')}-wayland.sh"
    )

    env_lines = [
        "#!/bin/sh",
        "set -eu",
        "export KS_DIR=\"" + KLIPPERSCREEN_DIR.as_posix() + "\"",
        "export KS_ENV=\"" + KLIPPERSCREEN_ENV_DIR.as_posix() + "\"",
        "export KS_XCLIENT=\"" +
        f"{KLIPPERSCREEN_ENV_DIR.as_posix()}/bin/python {KLIPPERSCREEN_DIR.as_posix()}/screen.py" +
        "\"",
        "export BACKEND=\"w\"",
        'export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"',
    ]

    for key, value in preset.env.items():
        escaped = value.replace("\"", "\\\"")
        env_lines.append(f'export {key}="{escaped}"')

    env_lines.append(
        f'exec "{KLIPPERSCREEN_DIR.joinpath("scripts/KlipperScreen-start.sh").as_posix()}" "$@"'
    )

    wrapper_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    os.chmod(wrapper_path, 0o755)
    Logger.print_info(f"Created Wayland wrapper: {wrapper_path}")
    return wrapper_path


def _write_desktop_entry(wrapper_path: Path, preset: WaylandPreset) -> Path:
    desktop_dir = Path.home().joinpath(".local/share/applications")
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_path = desktop_dir.joinpath(
        f"klipperscreen-{preset.name.lower().replace(' ', '-')}.desktop"
    )

    desktop_content = dedent(
        f"""
        [Desktop Entry]
        Type=Application
        Name=KlipperScreen ({preset.name})
        Comment=Launch KlipperScreen with the {preset.desktop} Wayland preset
        Exec={wrapper_path.as_posix()}
        Icon=klipperscreen
        Terminal=false
        Categories=Utility;System;
        Keywords=klipper;klipperscreen;wayland;
        """
    ).strip()

    desktop_path.write_text(desktop_content + "\n", encoding="utf-8")
    Logger.print_info(f"Desktop entry stored at {desktop_path}")

    return desktop_path


@dataclass
class _ServiceResult:
    backend: AutostartBackend
    path: Optional[Path]


def _write_user_service(wrapper_path: Path, preset: WaylandPreset) -> _ServiceResult:
    init_system = detect_init_system()
    if init_system == InitSystem.OPENRC:
        path = _write_openrc_service(wrapper_path, preset)
        return _ServiceResult(AutostartBackend.OPENRC, path)
    if init_system == InitSystem.SYSTEMD:
        path = _write_systemd_user_service(wrapper_path, preset)
        return _ServiceResult(AutostartBackend.SYSTEMD_USER, path)
    Logger.print_warn(
        "Unsupported init system for user services; generated desktop entry only."
    )
    return _ServiceResult(AutostartBackend.NONE, None)


def _write_systemd_user_service(wrapper_path: Path, preset: WaylandPreset) -> Path:
    user_systemd_dir = Path.home().joinpath(".config/systemd/user")
    user_systemd_dir.mkdir(parents=True, exist_ok=True)
    service_path = user_systemd_dir.joinpath(
        f"klipperscreen-{preset.name.lower().replace(' ', '-')}.service"
    )

    env_lines = "\n".join(
        (
            f'Environment="{key}={value}"'
            if " " in value
            else f"Environment={key}={value}"
        )
        for key, value in preset.env.items()
    )

    service_content = dedent(
        f"""
        [Unit]
        Description=KlipperScreen ({preset.name} Wayland preset)
        After=graphical-session.target
        PartOf=graphical-session.target

        [Service]
        Type=simple
        Restart=on-failure
        Environment=KS_DIR={KLIPPERSCREEN_DIR.as_posix()}
        Environment=KS_ENV={KLIPPERSCREEN_ENV_DIR.as_posix()}
        Environment="KS_XCLIENT={KLIPPERSCREEN_ENV_DIR.as_posix()}/bin/python {KLIPPERSCREEN_DIR.as_posix()}/screen.py"
        Environment=BACKEND=w
        Environment=XDG_RUNTIME_DIR=%t
        {env_lines}
        ExecStart={wrapper_path.as_posix()}

        [Install]
        WantedBy=default.target
        """
    ).strip()

    service_path.write_text(service_content + "\n", encoding="utf-8")

    return service_path


def _write_openrc_service(wrapper_path: Path, preset: WaylandPreset) -> Path:
    openrc_dir = Path.home().joinpath(".config/openrc")
    svc_dir = openrc_dir.joinpath("init.d")
    svc_dir.mkdir(parents=True, exist_ok=True)
    service_path = svc_dir.joinpath(
        f"klipperscreen-{preset.name.lower().replace(' ', '-')}"
    )

    content = dedent(
        f"""
        #!/sbin/openrc-run
        description="KlipperScreen ({preset.name} Wayland preset)"
        command="{wrapper_path.as_posix()}"
        command_background="yes"
        pidfile="/run/$RC_SVCNAME.pid"
        name="klipperscreen-{preset.name.lower().replace(' ', '-')}"

        depend() {{
            need net
        }}

        _kiauh_wait_for_moonraker() {{
            local url="${{MOONRAKER_URL:-http://127.0.0.1:7125/server/info}}"
            local tries=60
            local have_client=""
            if command -v wget >/dev/null 2>&1; then
                have_client="wget"
            elif command -v curl >/dev/null 2>&1; then
                have_client="curl"
            fi

            if [ -z "$have_client" ]; then
                ewarn "No curl/wget available to probe Moonraker; starting immediately."
                return 0
            fi

            while [ $tries -gt 0 ]; do
                if [ "$have_client" = "wget" ]; then
                    wget -qO- "$url" >/dev/null 2>&1 && return 0
                else
                    curl -fsS "$url" >/dev/null 2>&1 && return 0
                fi
                sleep 2
                tries=$((tries - 1))
            done
            ewarn "Moonraker did not become ready in time; continuing regardless."
            return 0
        }}

        start_pre() {{
            _kiauh_wait_for_moonraker
        }}
        """
    ).strip()

    service_path.write_text(content + "\n", encoding="utf-8")
    os.chmod(service_path, 0o755)
    
    return service_path


def _write_autostart_entry(wrapper_path: Path, preset: WaylandPreset, shell: str) -> Path:
    autostart_dir = Path.home().joinpath(".config/autostart")
    autostart_dir.mkdir(parents=True, exist_ok=True)
    autostart_path = autostart_dir.joinpath(
        f"klipperscreen-{preset.name.lower().replace(' ', '-')}-autostart.desktop"
    )

    only_show_in = ""
    shell_lower = shell.lower()
    if shell_lower == "phosh":
        only_show_in = "OnlyShowIn=GNOME;Phosh;"
    elif shell_lower == "plasma":
        only_show_in = "OnlyShowIn=KDE;Plasma;"

    content = dedent(
        f"""
        [Desktop Entry]
        Type=Application
        Name=KlipperScreen ({preset.name})
        Comment=Autostart KlipperScreen in the {preset.desktop} session
        Exec={wrapper_path.as_posix()}
        X-GNOME-Autostart-enabled=true
        {only_show_in}
        """
    ).strip()

    autostart_path.write_text(content + "\n", encoding="utf-8")
    return autostart_path


def _write_login_shell_snippet(wrapper_path: Path, preset: WaylandPreset) -> tuple[Path, Path]:
    profile_dir = Path.home().joinpath(".config/profile.d")
    profile_dir.mkdir(parents=True, exist_ok=True)
    snippet_path = profile_dir.joinpath("klipperscreen-autostart.sh")

    snippet_content = dedent(
        f"""
        # Auto-generated by KIAUH: start KlipperScreen once Moonraker is reachable.
        # shellcheck disable=SC1090
        if [ -n "$SSH_CONNECTION" ] || [ -n "$SSH_CLIENT" ]; then
            return 0
        fi
        if command -v pgrep >/dev/null 2>&1 && \
            pgrep -f "KlipperScreen-start.sh" >/dev/null 2>&1; then
            return 0
        fi
        moonraker_url="${{MOONRAKER_URL:-http://127.0.0.1:7125/server/info}}"
        tries=60
        while [ $tries -gt 0 ]; do
            if command -v wget >/dev/null 2>&1; then
                wget -qO- "$moonraker_url" >/dev/null 2>&1 && break
            elif command -v curl >/dev/null 2>&1; then
                curl -fsS "$moonraker_url" >/dev/null 2>&1 && break
            else
                echo "Neither wget nor curl available to probe Moonraker; skipping check." >&2
                break
            fi
            sleep 2
            tries=$((tries - 1))
        done
        if [ $tries -eq 0 ]; then
            echo "Moonraker not reachable; KlipperScreen autostart skipped." >&2
            return 0
        fi
        nohup {wrapper_path.as_posix()} >/dev/null 2>&1 &
        return 0
        """
    ).strip()

    snippet_path.write_text(snippet_content + "\n", encoding="utf-8")

    profile_path = Path.home().joinpath(".profile")
    inclusion_block = dedent(
        """
        # >>> KIAUH profile.d hook >>>
        for profile_snippet in "$HOME"/.config/profile.d/*.sh; do
            [ -r "$profile_snippet" ] && . "$profile_snippet"
        done
        # <<< KIAUH profile.d hook <<<
        """
    ).strip()

    if profile_path.exists():
        profile_contents = profile_path.read_text(encoding="utf-8")
        if inclusion_block not in profile_contents:
            if not profile_contents.endswith("\n"):
                profile_contents += "\n"
            profile_contents += inclusion_block + "\n"
            profile_path.write_text(profile_contents, encoding="utf-8")
    else:
        profile_contents = "#!/bin/sh\n" + inclusion_block + "\n"
        profile_path.write_text(profile_contents, encoding="utf-8")

    return snippet_path, profile_path


def _detect_mobile_shell() -> Optional[str]:
    candidates = [
        os.environ.get("XDG_CURRENT_DESKTOP", ""),
        os.environ.get("DESKTOP_SESSION", ""),
        os.environ.get("XDG_SESSION_DESKTOP", ""),
    ]
    combined = ":".join(filter(None, candidates)).lower()
    if "phosh" in combined:
        return "phosh"
    if "plasma" in combined or "plasma-mobile" in combined:
        return "plasma"
    if "sxmo" in combined:
        return "sxmo"
    return None


def _shell_matches_preset(shell: str, preset: WaylandPreset) -> bool:
    shell_lower = shell.lower()
    name_lower = preset.name.lower()
    if shell_lower == "phosh":
        return "phosh" in name_lower
    if shell_lower == "plasma":
        return "plasma" in name_lower
    if shell_lower == "sxmo":
        return "sxmo" in name_lower
    return False


def detect_internal_display() -> Optional[DisplayInfo]:
    detectors = [_detect_with_wlr_randr, _detect_with_weston_info]
    for detector in detectors:
        info = detector()
        if info:
            return info
    return None


def _detect_with_wlr_randr() -> Optional[DisplayInfo]:
    if shutil.which("wlr-randr") is None:
        return None
    try:
        result = run("wlr-randr", capture_output=True, text=True, check=True)
    except CalledProcessError:
        return None

    display: Optional[DisplayInfo] = None
    current_name: Optional[str] = None
    rotation: Optional[int] = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if not line.startswith(" "):
            if display and display.name:
                break
            current_name = line.split()[0]
            rotation = None
            continue

        if current_name and _looks_like_internal_connector(current_name):
            if "Transform:" in line:
                rotation = _transform_to_rotation(line.split("Transform:", 1)[1].strip())
            match = _extract_resolution(line)
            if match:
                width, height = match
                display = DisplayInfo(
                    name=current_name,
                    width=width,
                    height=height,
                    rotation=rotation,
                )
    return display


def _detect_with_weston_info() -> Optional[DisplayInfo]:
    if shutil.which("weston-info") is None:
        return None
    try:
        result = run("weston-info", capture_output=True, text=True, check=True)
    except CalledProcessError:
        return None

    display: Optional[DisplayInfo] = None
    current_name: Optional[str] = None
    rotation: Optional[int] = None

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("output"):
            _, current_name, *_ = line.split()
            rotation = None
            continue
        if not current_name or not _looks_like_internal_connector(current_name):
            continue
        if "transform" in line and "transform=" in line:
            rotation = _transform_to_rotation(line.split("transform=", 1)[1])
        match = _extract_resolution(line)
        if match:
            width, height = match
            display = DisplayInfo(
                name=current_name,
                width=width,
                height=height,
                rotation=rotation,
            )
            break
    return display


def _looks_like_internal_connector(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("edp", "dsi", "lvds", "panel", "default"))


def _extract_resolution(line: str) -> Optional[tuple[int, int]]:
    match = re.search(r"(\d{3,4})x(\d{3,4})", line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _transform_to_rotation(value: str) -> Optional[int]:
    lowered = value.lower()
    if "270" in lowered or "left" in lowered:
        return 270
    if "180" in lowered or "inverted" in lowered:
        return 180
    if "90" in lowered or "right" in lowered:
        return 90
    if "0" in lowered or "normal" in lowered:
        return 0
    return None


def preseed_klipperscreen_config(display: DisplayInfo) -> None:
    KLIPPERSCREEN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    width_line = f"width: {display.width}"
    height_line = f"height: {display.height}"
    rotation_hint = (
        f"# rotation_hint: {display.rotation}"
        if display.rotation is not None
        else "# rotation_hint: 0"
    )
    header = (
        f"# Auto-generated by KIAUH using {display.name} detection.\n"
        "# Adjust these values if the compositor applies a different scale or rotation.\n"
    )

    if not KLIPPERSCREEN_CONFIG_PATH.exists():
        content = "\n".join(["[main]", header.strip(), width_line, height_line, rotation_hint]) + "\n"
        KLIPPERSCREEN_CONFIG_PATH.write_text(content, encoding="utf-8")
        Logger.print_ok(
            f"Created KlipperScreen.conf with detected resolution {display.width}x{display.height}."
        )
        return

    existing = KLIPPERSCREEN_CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    updated = False
    if not any(line.startswith("width:") for line in existing):
        existing.append(width_line)
        updated = True
    if not any(line.startswith("height:") for line in existing):
        existing.append(height_line)
        updated = True
    if rotation_hint not in existing:
        existing.append(rotation_hint)
        updated = True
    if updated:
        KLIPPERSCREEN_CONFIG_PATH.write_text("\n".join(existing) + "\n", encoding="utf-8")
        Logger.print_ok("Updated KlipperScreen.conf with detected display defaults.")


def _read_backend_choice(path: Path) -> Optional[str]:
    try:
        raw = path.read_text(encoding="utf-8").strip().upper()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    if raw in {"X", "W"}:
        return raw
    return None


def install_klipperscreen() -> None:
    Logger.print_status("Installing KlipperScreen ...")

    if not check_python_version(3, 7):
        return

    selected_preset: Optional[WaylandPreset] = None

    mr_instances = get_instances(Moonraker)
    if not mr_instances:
        Logger.print_dialog(
            DialogType.WARNING,
            [
                "Moonraker not found! KlipperScreen will not properly work "
                "without a working Moonraker installation.",
                "\n\n",
                "KlipperScreens update manager configuration for Moonraker "
                "will not be added to any moonraker.conf.",
            ],
        )
        if not get_confirm(
            "Continue KlipperScreen installation?",
            default_choice=False,
            allow_go_back=True,
        ):
            return

    check_install_dependencies()

    git_clone_wrapper(KLIPPERSCREEN_REPO, KLIPPERSCREEN_DIR)
    _sync_installer_script_with_asset()
    _ensure_start_script_client_fallback()

    backend_track_path = KLIPPERSCREEN_INSTALL_SCRIPT.parent.joinpath(
        BACKEND_TRACK_FILENAME
    )
    if backend_track_path.exists():
        try:
            backend_track_path.unlink()
        except OSError:
            pass

    env = os.environ.copy()
    env["KIAUH_BACKEND_TRACK_FILE"] = backend_track_path.as_posix()

    extras_choice = get_confirm(
        "Install optional KlipperScreen extras (fonts and media helpers)?",
        default_choice=False,
        allow_go_back=True,
    )
    if extras_choice is None:
        return
    env["KIAUH_KS_INSTALL_EXTRAS"] = "1" if extras_choice else "0"

    try:
        run(
            KLIPPERSCREEN_INSTALL_SCRIPT.as_posix(),
            shell=True,
            check=True,
            env=env,
        )

        backend_choice = _read_backend_choice(backend_track_path)
        if backend_choice == "W":
            selected_preset = prompt_wayland_preset()
        elif backend_choice == "X":
            Logger.print_info(
                "Skipping Wayland preset generation because the X11 backend was selected."
            )
        else:
            if get_confirm(
                "Configure a Wayland preset anyway?",
                default_choice=False,
                allow_go_back=False,
            ):
                selected_preset = prompt_wayland_preset()

        autostart_result: Optional[AutostartResult] = None
        if selected_preset is not None:
            try:
                autostart_result = configure_wayland_launchers(selected_preset)
            except Exception:  # pragma: no cover - already logged inside helper
                autostart_result = None

        init_system = detect_init_system()
        manage_systemd_service = init_system is InitSystem.SYSTEMD
        if autostart_result is not None and autostart_result.uses_user_autostart:
            manage_systemd_service = False

        if mr_instances:
            patch_klipperscreen_update_manager(
                mr_instances,
                manage_systemd_service=manage_systemd_service,
            )
            InstanceManager.restart_all(mr_instances)
        else:
            Logger.print_info(
                "Moonraker is not installed! Cannot add "
                "KlipperScreen to update manager!"
            )
        display_info = detect_internal_display()
        if display_info is not None:
            preseed_klipperscreen_config(display_info)
        Logger.print_ok("KlipperScreen successfully installed!")
    except CalledProcessError as e:
        Logger.print_error(f"Error installing KlipperScreen:\n{e}")
        return
    finally:
        if backend_track_path.exists():
            try:
                backend_track_path.unlink()
            except OSError:
                pass


def patch_klipperscreen_update_manager(
    instances: List[Moonraker],
    *,
    manage_systemd_service: bool = True,
) -> None:
    BackupService().backup_moonraker_conf()
    options = [
        ("type", "git_repo"),
        ("path", KLIPPERSCREEN_DIR.as_posix()),
        ("origin", KLIPPERSCREEN_REPO),
        ("env", f"{KLIPPERSCREEN_ENV_DIR}/bin/python"),
        ("requirements", KLIPPERSCREEN_REQ_FILE.as_posix()),
        ("install_script", KLIPPERSCREEN_INSTALL_SCRIPT.as_posix()),
    ]
    if manage_systemd_service:
        options.insert(3, ("managed_services", "KlipperScreen"))

    add_config_section(
        section=KLIPPERSCREEN_UPDATER_SECTION_NAME,
        instances=instances,
        options=options,
    )


def update_klipperscreen() -> None:
    if not KLIPPERSCREEN_DIR.exists():
        Logger.print_info("KlipperScreen does not seem to be installed! Skipping ...")
        return

    try:
        Logger.print_status("Updating KlipperScreen ...")

        cmd_sysctl_service(KLIPPERSCREEN_SERVICE_NAME, "stop")

        settings = KiauhSettings()
        if settings.kiauh.backup_before_update:
            backup_klipperscreen_dir()

        git_pull_wrapper(KLIPPERSCREEN_DIR)

        install_python_requirements(KLIPPERSCREEN_ENV_DIR, KLIPPERSCREEN_REQ_FILE)

        cmd_sysctl_service(KLIPPERSCREEN_SERVICE_NAME, "start")

        Logger.print_ok("KlipperScreen updated successfully.", end="\n\n")
    except CalledProcessError as e:
        Logger.print_error(f"Error updating KlipperScreen:\n{e}")
        return


def get_klipperscreen_status() -> ComponentStatus:
    service_dir = get_service_directory()
    return get_install_status(
        KLIPPERSCREEN_DIR,
        KLIPPERSCREEN_ENV_DIR,
        files=[service_dir.joinpath(KLIPPERSCREEN_SERVICE_NAME)],
    )


def remove_klipperscreen() -> None:
    Logger.print_status("Removing KlipperScreen ...")
    try:
        if KLIPPERSCREEN_DIR.exists():
            Logger.print_status("Removing KlipperScreen directory ...")
            shutil.rmtree(KLIPPERSCREEN_DIR)
            Logger.print_ok("KlipperScreen directory successfully removed!")
        else:
            Logger.print_warn("KlipperScreen directory not found!")

        if KLIPPERSCREEN_ENV_DIR.exists():
            Logger.print_status("Removing KlipperScreen environment ...")
            shutil.rmtree(KLIPPERSCREEN_ENV_DIR)
            Logger.print_ok("KlipperScreen environment successfully removed!")
        else:
            Logger.print_warn("KlipperScreen environment not found!")

        if KLIPPERSCREEN_SERVICE_FILE.exists():
            remove_system_service(KLIPPERSCREEN_SERVICE_NAME)

        logfile = Path(f"/tmp/{KLIPPERSCREEN_LOG_NAME}")
        if logfile.exists():
            Logger.print_status("Removing KlipperScreen log file ...")
            remove_with_sudo(logfile)
            Logger.print_ok("KlipperScreen log file successfully removed!")

        kl_instances: List[Klipper] = get_instances(Klipper)
        for instance in kl_instances:
            logfile = instance.base.log_dir.joinpath(KLIPPERSCREEN_LOG_NAME)
            if logfile.exists():
                Logger.print_status(f"Removing {logfile} ...")
                Path(logfile).unlink()
                Logger.print_ok(f"{logfile} successfully removed!")

        mr_instances: List[Moonraker] = get_instances(Moonraker)
        if mr_instances:
            Logger.print_status("Removing KlipperScreen from update manager ...")
            BackupService().backup_moonraker_conf()
            remove_config_section("update_manager KlipperScreen", mr_instances)
            Logger.print_ok("KlipperScreen successfully removed from update manager!")

        Logger.print_ok("KlipperScreen successfully removed!")

    except Exception as e:
        Logger.print_error(f"Error removing KlipperScreen:\n{e}")


def backup_klipperscreen_dir() -> None:
    svc = BackupService()
    svc.backup_directory(
        source_path=KLIPPERSCREEN_DIR,
        backup_name="KlipperScreen",
        target_path="KlipperScreen",
    )
    svc.backup_directory(
        source_path=KLIPPERSCREEN_ENV_DIR,
        backup_name="KlipperScreen-env",
        target_path="KlipperScreen",
    )

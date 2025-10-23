"""Helpers for caching sudo credentials during a KIAUH session."""

from __future__ import annotations

import shutil
import subprocess
import threading
from subprocess import DEVNULL

from core.logger import Logger
from utils.input_utils import get_confirm


_GLOBAL_SESSION: "SudoSession" | None = None


def get_sudo_session() -> "SudoSession":
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        _GLOBAL_SESSION = SudoSession()
    return _GLOBAL_SESSION


def ensure_sudo_session() -> None:
    session = get_sudo_session()
    session.ensure_active()


def shutdown_sudo_session() -> None:
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        return
    _GLOBAL_SESSION.close()
    _GLOBAL_SESSION = None


class SudoSession:
    """Cache sudo credentials for the lifetime of a KIAUH session."""

    def __init__(self, refresh_interval: int = 60) -> None:
        self.refresh_interval = refresh_interval
        self._prompted = False
        self._enabled = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._refresh_cmd: list[str] | None = ["sudo", "-n", "-v"]

    def ensure_active(self) -> None:
        """Prompt for caching when first sudo access is required."""

        if self._prompted:
            return

        self._prompted = True

        if shutil.which("sudo") is None:
            return

        Logger.print_info(
            "KIAUH can cache your sudo credentials until you exit the helper."
        )
        Logger.print_info(
            "The password is only held in sudo's own timestamp cache and is cleared when you leave."
        )

        consent = get_confirm(
            "Cache your sudo password for this KIAUH session?",
            default_choice=True,
        )

        if not consent:
            return

        Logger.print_status("Priming sudo credential cache ...")

        try:
            result = subprocess.run(
                ["sudo", "-v"], capture_output=True, text=True
            )
        except KeyboardInterrupt:
            Logger.print_warn(
                "Cancelled sudo credential caching. Continuing without it."
            )
            return

        if result.returncode != 0:
            if self._is_option_unsupported(result.stderr):
                Logger.print_warn(
                    "This sudo implementation does not support credential caching."
                )
            else:
                Logger.print_warn(
                    "Unable to cache sudo credentials. Commands will prompt as usual."
                )
            return

        self._enabled = True
        Logger.print_ok("Cached sudo credentials for this session.")

        self._refresh_cmd = self._select_refresh_command()
        if self._refresh_cmd is None:
            Logger.print_warn(
                "Automatic sudo refresh is unavailable. Credentials may expire during this session."
            )
            return

        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def close(self) -> None:
        """Stop refreshing and clear cached credentials."""

        if shutil.which("sudo") is None:
            return

        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

        if self._enabled:
            subprocess.run(["sudo", "-k"], stdout=DEVNULL, stderr=DEVNULL)

        self._thread = None
        self._enabled = False
        self._stop_event.clear()

    def _refresh_loop(self) -> None:
        if self._refresh_cmd is None:
            return

        while not self._stop_event.wait(self.refresh_interval):
            result = subprocess.run(
                self._refresh_cmd,
                stdout=DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                continue

            if self._is_option_unsupported(result.stderr) and self._refresh_cmd != [
                "sudo",
                "-v",
            ]:
                self._refresh_cmd = ["sudo", "-v"]
                continue

            Logger.print_warn(
                "The cached sudo credentials expired. Future commands may prompt again."
            )
            self._enabled = False
            return

    @staticmethod
    def _is_option_unsupported(stderr: str | None) -> bool:
        if not stderr:
            return False
        stderr_lower = stderr.lower()
        return "unrecognized option" in stderr_lower or "invalid option" in stderr_lower

    def _select_refresh_command(self) -> list[str] | None:
        candidates = [["sudo", "-n", "-v"], ["sudo", "-v"]]
        for cmd in candidates:
            result = subprocess.run(
                cmd,
                stdout=DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                return cmd
            if not self._is_option_unsupported(result.stderr):
                break
        return None

"""Helpers for caching sudo credentials during a KIAUH session."""

from __future__ import annotations

import shutil
import subprocess
import threading
from subprocess import DEVNULL

from core.logger import Logger
from utils.input_utils import get_confirm


class SudoSession:
    """Cache sudo credentials for the lifetime of a KIAUH session."""

    def __init__(self, refresh_interval: int = 60) -> None:
        self.refresh_interval = refresh_interval
        self._prompted = False
        self._enabled = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def maybe_enable(self) -> None:
        """Ask the user whether KIAUH should keep sudo alive for this run."""

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
            result = subprocess.run(["sudo", "-v"])
        except KeyboardInterrupt:
            Logger.print_warn("Cancelled sudo credential caching. Continuing without it.")
            return

        if result.returncode != 0:
            Logger.print_warn(
                "Unable to cache sudo credentials. Commands will prompt as usual."
            )
            return

        self._enabled = True
        Logger.print_ok("Cached sudo credentials for this session.")

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
        while not self._stop_event.wait(self.refresh_interval):
            result = subprocess.run(
                ["sudo", "-n", "-v"], stdout=DEVNULL, stderr=DEVNULL
            )
            if result.returncode != 0:
                Logger.print_warn(
                    "The cached sudo credentials expired. Future commands may prompt again."
                )
                self._enabled = False
                return

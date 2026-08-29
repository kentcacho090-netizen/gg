#!/usr/bin/env python3
"""Small Android controller for the Termux CoC automation project.

This replaces the Windows-only pyautogui/pywinauto layer from the reference
project with Android's native `input` and `screencap` commands.

It intentionally contains NO game strategy. It only captures the screen and
performs an explicitly requested tap, which makes it safe to test the vision
pipeline before enabling automation.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


class AndroidController:
    def __init__(self, screenshot_path: str | os.PathLike = "autoc_test.png"):
        self.screenshot_path = Path(screenshot_path).expanduser().resolve()
        self.screenshot_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _run(*args: str, timeout: float = 15.0) -> subprocess.CompletedProcess:
        return subprocess.run(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )

    def capture(self) -> Path:
        """Capture the Android display directly into the Termux filesystem."""
        result = self._run("/system/bin/screencap", "-p", str(self.screenshot_path))
        if result.returncode != 0 or not self.screenshot_path.exists():
            raise RuntimeError(
                "Android screencap failed: "
                + (result.stderr.strip() or result.stdout.strip() or "unknown error")
            )
        if self.screenshot_path.stat().st_size < 10_000:
            raise RuntimeError("Screenshot was created but is unexpectedly small")
        return self.screenshot_path

    def tap(self, x: float, y: float) -> None:
        """Tap one screen coordinate using Android's native input command."""
        x_i, y_i = int(round(x)), int(round(y))
        result = self._run("/system/bin/input", "tap", str(x_i), str(y_i))
        if result.returncode != 0:
            raise RuntimeError(
                "Android tap failed: "
                + (result.stderr.strip() or result.stdout.strip() or "unknown error")
            )

    def wait_for_screen_change(self, before: Path, delay: float = 0.35) -> Path:
        """Take a second screenshot after a short delay.

        The caller can compare the two images to verify that a tap actually
        changed the screen before proceeding with any further action.
        """
        time.sleep(max(0.0, delay))
        return self.capture()

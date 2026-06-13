"""Regression tests for the CLI entrypoints that can't be exercised in-process.

`python -m tripplanner` and `python run_cli.py` run the package as a subprocess,
so they're validated by actually invoking them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tripplanner import __version__

_ROOT = Path(__file__).resolve().parent.parent


def test_module_entrypoint_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tripplanner", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert __version__ in result.stdout


def test_run_cli_shim_version() -> None:
    result = subprocess.run(
        [sys.executable, str(_ROOT / "run_cli.py"), "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert __version__ in result.stdout

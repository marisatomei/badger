#!/usr/bin/env python3
"""GitHub Universe 2026 Badge Simulator.

Runs Universe 2026 badge applications locally via Pygame by simulating the
2026 MicroPython runtime globals (badge, screen, image, font, color, shape,
brush, vec2, rect, mat3, run, button constants, display modes, and State).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    import pygame  # noqa: F401
except ImportError:
    # Auto-detect local virtual environment if active shell didn't activate it
    _candidates = [
        REPO_ROOT / ".venv" / "bin" / "python3",
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "Scripts" / "python3.exe",
    ]
    _venv_py = next((c for c in _candidates if c.exists()), None)
    if _venv_py and Path(sys.executable).resolve() != _venv_py.resolve():
        os.execv(str(_venv_py), [str(_venv_py)] + sys.argv)
    raise SystemExit(
        "Pygame is required to run the Universe 2026 Badge Simulator.\n"
        "Run 'make setup' to set up the environment, or run: pip install pygame-ce"
    )

from sim26.mocks import State, install_mock_modules  # noqa: E402, F401
from sim26.primitives import (  # noqa: E402, F401
    ColorObj,
    ImageBrush,
    ShapeObj,
    brush,
    color,
    mat3,
    normalize_color,
    rect,
    shape,
    vec2,
)
from sim26.runtime import (  # noqa: E402, F401
    BUTTON_BACK,
    BUTTON_DOWN,
    BUTTON_HOME,
    BUTTON_LEFT,
    BUTTON_MENU,
    BUTTON_RIGHT,
    BUTTON_SELECT,
    BUTTON_UP,
    ELLIPSES,
    HIRES,
    KEY_MAP,
    LORES,
    VSYNC,
    BadgeRuntime,
    Button,
    ButtonGroup,
    DisplayMock,
    RunResult,
    SimulatorApp,
)
from sim26.screen import FontWrapper, Image, Screen, SpriteSheet, font, image  # noqa: E402, F401
from sim26.vfs import (  # noqa: E402, F401
    APPS_DIR,
    BADGE_ROOT,
    STATE_DIR,
    install_vfs_hooks,
    map_system_path,
)

install_vfs_hooks()


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub Universe 2026 Badge Simulator")
    parser.add_argument("app", nargs="?", default="menu", help="App name under badge/apps/ (default: menu)")
    parser.add_argument("--scale", type=int, default=4, help="Display scale factor (default: 4)")
    parser.add_argument("--screenshots", help="Directory to save screenshots when pressing F12")
    parser.add_argument("--perf", action="store_true", help="Print live performance statistics")
    parser.add_argument("--clean", action="store_true", help="Remove saved state before running")
    parser.add_argument("--frames", type=int, default=None, help="Exit after N frames (useful for headless testing)")
    parser.add_argument("--save-screenshot", help="Save final frame image to this path on exit")

    args = parser.parse_args()

    if args.clean and STATE_DIR.exists():
        shutil.rmtree(STATE_DIR)
        print("[Simulator] Cleared .badge_state directory.")

    install_mock_modules()

    app_name = args.app.strip()
    if "/" in app_name:
        app_path = map_system_path(app_name)
    else:
        app_path = str(APPS_DIR / app_name)

    sim = SimulatorApp(
        scale=args.scale,
        screenshots_dir=Path(args.screenshots) if args.screenshots else None,
        perf=args.perf,
        max_frames=args.frames,
        save_screenshot=Path(args.save_screenshot) if args.save_screenshot else None,
    )

    sim.launch(app_path)
    while sim.running and sim.next_app_to_launch:
        next_app = sim.next_app_to_launch
        sim.next_app_to_launch = None
        sim.launch(next_app)

    return 0


if __name__ == "__main__":
    sys.exit(main())

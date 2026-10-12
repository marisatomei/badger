#!/usr/bin/env python3
"""GitHub Universe 2026 Badge Development CLI Helper.

Zero-dependency tool to validate apps, scaffold new apps, and interface with
the physical badge using mpremote.
"""

from __future__ import annotations

import argparse
import ast
import os
import py_compile
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BADGE_ROOT = REPO_ROOT / "badge"
APPS_DIR = BADGE_ROOT / "apps"


def parse_png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read PNG width and height from header without external libraries."""
    try:
        with open(path, "rb") as f:
            data = f.read(32)
            if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", data[16:24])
    except Exception:
        pass
    return None


def generate_png_icon(width: int = 24, height: int = 24, r: int = 40, g: int = 120, b: int = 220) -> bytes:
    """Generate a valid 24x24 PNG icon using pure standard library."""
    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        for x in range(width):
            # Draw a subtle border and colored background
            if x in (0, width - 1) or y in (0, height - 1):
                raw.extend([max(0, r - 30), max(0, g - 30), max(0, b - 30)])
            elif x in (2, 3, width - 4, width - 3) and y in (2, 3, height - 4, height - 3):
                raw.extend([min(255, r + 60), min(255, g + 60), min(255, b + 60)])
            else:
                raw.extend([r, g, b])

    compressed = zlib.compress(bytes(raw))
    idat_crc = zlib.crc32(b"IDAT" + compressed)
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

    iend_crc = zlib.crc32(b"IEND")
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return header + ihdr + idat + iend


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate badge codebase, app structures, and guidelines."""
    print("========================================")
    print(" GitHub Universe 2026 App Validator")
    print("========================================\n")

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Check secrets.py
    secrets_path = BADGE_ROOT / "secrets.py"
    if secrets_path.exists():
        content = secrets_path.read_text(encoding="utf-8")
        # Check for non-empty credentials
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if v and ("password" in k.lower() or "secret" in k.lower() or "token" in k.lower()):
                    errors.append(f"secrets.py: sensitive field '{k}' contains non-empty value in source control!")
        print("✓ badge/secrets.py checked")
    else:
        warnings.append("badge/secrets.py not found")

    # 2. Syntax check main.py
    main_path = BADGE_ROOT / "main.py"
    if main_path.exists():
        try:
            py_compile.compile(str(main_path), doraise=True)
            print("✓ badge/main.py syntax OK")
        except py_compile.PyCompileError as e:
            errors.append(f"badge/main.py syntax error: {e}")

    # 3. Check apps
    if not APPS_DIR.exists():
        errors.append(f"Apps directory not found at {APPS_DIR}")
        return 1

    app_dirs = sorted([p for p in APPS_DIR.iterdir() if p.is_dir()])
    print(f"\nChecking {len(app_dirs)} apps under badge/apps/:\n")

    legacy_badgeware_imports = re.compile(
        r"from\s+badgeware\s+import\s+.*(screen|Image|PixelFont|io|brushes|shapes)"
    )
    legacy_buttons = re.compile(r"\bBUTTON_[ABC]\b")

    special_apps = {"menu", "startup"}

    for app in app_dirs:
        app_name = app.name
        app_status = "PASS"
        app_issues: list[str] = []

        init_file = app / "__init__.py"
        icon_file = app / "icon.png"

        # Check __init__.py
        if not init_file.exists():
            app_issues.append("Missing __init__.py")
        else:
            try:
                py_compile.compile(str(init_file), doraise=True)
                code_text = init_file.read_text(encoding="utf-8")

                # Check for legacy 2025 imports
                if legacy_badgeware_imports.search(code_text):
                    app_issues.append(
                        "Uses legacy Universe 2025 badgeware imports. Use 2026 globals instead."
                    )

                # Check AST for syntax and legacy button identifier usage
                tree = ast.parse(code_text, filename=str(init_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id in ("BUTTON_A", "BUTTON_B", "BUTTON_C"):
                        app_issues.append(
                            f"Uses legacy identifier {node.id} on line {node.lineno}. Use logical actions (BUTTON_SELECT, BUTTON_UP, etc.)."
                        )
                        break

            except (py_compile.PyCompileError, SyntaxError) as e:
                app_issues.append(f"Syntax error in __init__.py: {e}")

        # Check icon.png
        if not icon_file.exists():
            if app_name not in special_apps:
                warnings.append(f"{app_name}: Missing icon.png (24x24 recommended)")
        else:
            dims = parse_png_dimensions(icon_file)
            if not dims:
                app_issues.append("icon.png is not a valid PNG file")
            elif dims != (24, 24):
                app_issues.append(f"icon.png is {dims[0]}x{dims[1]} (must be 24x24)")

        # Compile any other .py files in app
        for py_file in app.glob("**/*.py"):
            if py_file == init_file:
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                app_issues.append(f"Syntax error in {py_file.name}: {e}")

        if app_issues:
            app_status = "FAIL"
            errors.extend([f"[{app_name}] {iss}" for iss in app_issues])
            print(f"  ✗ {app_name:<28} FAIL - {', '.join(app_issues)}")
        else:
            print(f"  ✓ {app_name:<28} OK")

    print("\n----------------------------------------")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
        print()

    if errors:
        print(f"Errors found ({len(errors)}):")
        for err in errors:
            print(f"  ✗ {err}")
        print("\nValidation FAILED.")
        return 1

    print("All checks passed successfully! ✨")
    return 0


def cmd_new_app(args: argparse.Namespace) -> int:
    """Scaffold a new Universe 2026 badge app."""
    name = args.name.strip().lower()
    if not re.match(r"^[a-z0-9_]+$", name):
        print(f"Error: Invalid app name '{name}'. Use lowercase letters, digits, and underscores only.")
        return 1

    target = APPS_DIR / name
    if target.exists():
        print(f"Error: App directory '{target}' already exists!")
        return 1

    target.mkdir(parents=True)
    (target / "assets").mkdir()

    title = name.replace("_", " ").title()

    init_code = f'''import os
import sys

APP_DIR = "/system/apps/{name}"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

screen.font = font.nope

# App state
message = "{title}"
color_index = 0
colors = [
    color.rgb(73, 219, 255),
    color.rgb(255, 107, 107),
    color.rgb(107, 255, 142),
    color.rgb(255, 217, 61),
]


def update():
    global color_index

    # Clear screen with dark background
    screen.pen = color.rgb(20, 24, 28)
    screen.rectangle(screen.clip)

    # Handle input using orientation-aware logical constants
    if badge.pressed(BUTTON_SELECT):
        color_index = (color_index + 1) % len(colors)

    # Draw title
    screen.pen = colors[color_index]
    screen.text(message, 10, 10)

    # Draw instructions
    screen.pen = color.rgb(160, 160, 160)
    screen.text("Press SELECT to change color", 10, screen.height - 20)


run(update)
'''

    (target / "__init__.py").write_text(init_code, encoding="utf-8")
    icon_bytes = generate_png_icon(24, 24, r=60, g=130, b=240)
    (target / "icon.png").write_bytes(icon_bytes)

    print(f"✓ Created new app '{name}' at badge/apps/{name}/")
    print(f"  ├── __init__.py  (starter 2026 app loop)")
    print(f"  ├── icon.png      (24x24 PNG menu icon)")
    print(f"  └── assets/       (assets folder)")
    print(f"\nTo test or deploy:")
    print(f"  python3 tools/badge.py validate")
    print(f"  python3 tools/badge.py deploy {name}")
    return 0


def find_badge_port() -> str | None:
    """Find connected badge serial port."""
    # Try mpremote devs first
    try:
        res = subprocess.run(["mpremote", "devs"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "2e8a:1101" in line or "Pimoroni" in line or "Tufty" in line:
                    parts = line.split()
                    if parts:
                        return parts[0]
            # Fallback to first usbmodem in mpremote devs
            for line in res.stdout.splitlines():
                if "/dev/cu.usbmodem" in line or "/dev/ttyACM" in line:
                    return line.split()[0]
    except FileNotFoundError:
        pass

    # Check /dev on macOS / Linux
    for dev_pattern in ["/dev/cu.usbmodem*", "/dev/ttyACM*"]:
        import glob
        matches = glob.glob(dev_pattern)
        if matches:
            return sorted(matches)[0]

    return None


def cmd_devs(args: argparse.Namespace) -> int:
    """List connected MicroPython / Tufty 2350 devices."""
    print("Scanning for connected badge devices...\n")
    try:
        res = subprocess.run(["mpremote", "devs"], check=False)
        return res.returncode
    except FileNotFoundError:
        print("Notice: 'mpremote' command not found in PATH.")
        print("Checking serial devices in filesystem:")
        port = find_badge_port()
        if port:
            print(f"Found potential badge serial port: {port}")
        else:
            print("No /dev/cu.usbmodem* or /dev/ttyACM* serial devices detected.")
        print("\nRun 'source .venv/bin/activate' or 'pip install mpremote' to enable full badge control.")
        return 0


def cmd_repl(args: argparse.Namespace) -> int:
    """Open interactive MicroPython REPL on connected badge."""
    port = args.port or find_badge_port()
    cmd = ["mpremote"]
    if port:
        cmd.extend(["connect", port])
    cmd.append("repl")
    print(f"Connecting to REPL ({port or 'auto'})... (Press Ctrl-] to exit)")
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError:
        print("Error: 'mpremote' not installed. Install with 'pip install mpremote' or 'make setup'.")
        return 1


def cmd_ls(args: argparse.Namespace) -> int:
    """List files on connected badge."""
    port = args.port or find_badge_port()
    path = args.path or ":/system/apps"
    cmd = ["mpremote"]
    if port:
        cmd.extend(["connect", port])
    cmd.extend(["fs", "ls", path])
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError:
        print("Error: 'mpremote' not installed. Install with 'pip install mpremote' or 'make setup'.")
        return 1


def cmd_reset(args: argparse.Namespace) -> int:
    """Reset the connected badge."""
    port = args.port or find_badge_port()
    cmd = ["mpremote"]
    if port:
        cmd.extend(["connect", port])
    cmd.append("reset")
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError:
        print("Error: 'mpremote' not installed. Install with 'pip install mpremote' or 'make setup'.")
        return 1


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy app or mount workspace on connected badge."""
    app_name = args.app
    app_dir = APPS_DIR / app_name
    if not app_dir.exists():
        print(f"Error: App '{app_name}' does not exist at {app_dir}")
        return 1

    port = args.port or find_badge_port()

    print(f"Deploying '{app_name}' to badge (port: {port or 'auto'})...")
    print("Note: On production 2026 firmware, /system is mounted read-only in raw REPL.")
    print("Using 'mpremote mount badge' allows live testing from host without flashing.")
    print("For persistent installs, boot into USB Mass Storage mode (double-tap Reset or run mass_storage app).\n")

    if args.mount:
        cmd = ["mpremote"]
        if port:
            cmd.extend(["connect", port])
        cmd.extend(["mount", str(BADGE_ROOT)])
        print(f"Running: {' '.join(cmd)}")
        try:
            return subprocess.run(cmd).returncode
        except FileNotFoundError:
            print("Error: 'mpremote' not installed.")
            return 1
    else:
        # Copy to badge
        cmd = ["mpremote"]
        if port:
            cmd.extend(["connect", port])
        remote_app_path = f":/system/apps/{app_name}"
        cmd.extend(["fs", "cp", "-r", str(app_dir), remote_app_path])
        print(f"Running: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd)
            if res.returncode == 0:
                print(f"✓ App '{app_name}' uploaded. Resetting badge...")
                subprocess.run(["mpremote", "reset"])
            return res.returncode
        except FileNotFoundError:
            print("Error: 'mpremote' not installed.")
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub Universe 2026 Badge Developer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    sub_val = subparsers.add_parser("validate", help="Validate all badge apps and code guidelines")

    # new-app
    sub_new = subparsers.add_parser("new-app", help="Scaffold a new 2026 badge app")
    sub_new.add_argument("name", help="Name of new app (e.g. hello_world)")

    # devs
    subparsers.add_parser("devs", help="Scan for connected badge devices")

    # repl
    sub_repl = subparsers.add_parser("repl", help="Open MicroPython REPL on connected badge")
    sub_repl.add_argument("--port", "-p", help="Serial port (e.g. /dev/cu.usbmodem2101)")

    # ls
    sub_ls = subparsers.add_parser("ls", help="List files on connected badge")
    sub_ls.add_argument("path", nargs="?", default=":/system/apps", help="Remote path (default: :/system/apps)")
    sub_ls.add_argument("--port", "-p", help="Serial port")

    # reset
    sub_reset = subparsers.add_parser("reset", help="Reset connected badge")
    sub_reset.add_argument("--port", "-p", help="Serial port")

    # deploy
    sub_dep = subparsers.add_parser("deploy", help="Deploy or mount app on connected badge")
    sub_dep.add_argument("app", help="App name under badge/apps/")
    sub_dep.add_argument("--mount", "-m", action="store_true", help="Mount badge folder on device instead of copying")
    sub_dep.add_argument("--port", "-p", help="Serial port")

    args = parser.parse_args()

    handlers = {
        "validate": cmd_validate,
        "new-app": cmd_new_app,
        "devs": cmd_devs,
        "repl": cmd_repl,
        "ls": cmd_ls,
        "reset": cmd_reset,
        "deploy": cmd_deploy,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

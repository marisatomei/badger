"""Unit tests for GitHub Universe 2026 Badge apps and codebase."""

import ast
import os
import py_compile
import re
import struct
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BADGE_ROOT = REPO_ROOT / "badge"
APPS_DIR = BADGE_ROOT / "apps"


def parse_png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as f:
            data = f.read(32)
            if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", data[16:24])
    except Exception:
        pass
    return None


class TestBadgeApps(unittest.TestCase):
    """Test suite for badge apps and standards."""

    def test_main_py_compiles(self):
        main_py = BADGE_ROOT / "main.py"
        self.assertTrue(main_py.exists(), "badge/main.py must exist")
        py_compile.compile(str(main_py), doraise=True)

    def test_secrets_py_no_sensitive_values(self):
        secrets_py = BADGE_ROOT / "secrets.py"
        if secrets_py.exists():
            content = secrets_py.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("#") or not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if v and any(s in k.lower() for s in ["password", "secret", "token", "key"]):
                    self.fail(f"Sensitive key '{k}' has a committed value in badge/secrets.py")

    def test_all_apps_have_init_and_valid_syntax(self):
        app_dirs = [p for p in APPS_DIR.iterdir() if p.is_dir()]
        self.assertGreater(len(app_dirs), 0, "No apps found in badge/apps/")

        legacy_badgeware = re.compile(
            r"from\s+badgeware\s+import\s+.*(screen|Image|PixelFont|io|brushes|shapes)"
        )

        for app in app_dirs:
            with self.subTest(app=app.name):
                init_file = app / "__init__.py"
                self.assertTrue(init_file.exists(), f"App {app.name} is missing __init__.py")

                # Syntax compile check
                py_compile.compile(str(init_file), doraise=True)

                code = init_file.read_text(encoding="utf-8")

                # Disallow legacy 2025 imports
                self.assertFalse(
                    legacy_badgeware.search(code),
                    f"App {app.name} uses legacy 2025 badgeware imports. Use 2026 runtime globals.",
                )

                # Disallow direct AST Name references to BUTTON_A, BUTTON_B, BUTTON_C
                tree = ast.parse(code, filename=str(init_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id in ("BUTTON_A", "BUTTON_B", "BUTTON_C"):
                        self.fail(
                            f"App {app.name} uses legacy button identifier {node.id} on line {node.lineno}"
                        )

    def test_icons_are_24x24(self):
        for icon in APPS_DIR.glob("*/icon.png"):
            with self.subTest(icon=icon):
                dims = parse_png_dimensions(icon)
                self.assertIsNotNone(dims, f"{icon} is not a valid PNG")
                self.assertEqual(dims, (24, 24), f"{icon} must be exactly 24x24, got {dims}")

    def test_scaffold_new_app(self):
        from tools.badge import generate_png_icon
        png_data = generate_png_icon(24, 24)
        self.assertTrue(png_data.startswith(b"\x89PNG\r\n\x1a\n"))
        w, h = struct.unpack(">II", png_data[16:24])
        self.assertEqual((w, h), (24, 24))

    def test_simulator_headless_smoke_runs(self):
        """Smoke test 2026 simulator headlessly for key apps."""
        sim_path = REPO_ROOT / "tools" / "simulator26.py"
        self.assertTrue(sim_path.exists(), "tools/simulator26.py must exist")

        env = os.environ.copy()
        env["SDL_VIDEODRIVER"] = "dummy"

        for app_name in ["menu", "flappy", "clock", "input_test"]:
            with self.subTest(app=app_name):
                res = subprocess.run(
                    [sys.executable, str(sim_path), app_name, "--frames", "3"],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"Simulator crashed on {app_name}:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
                )
                self.assertNotIn("Crash in", res.stdout)
                self.assertNotIn("Crash in", res.stderr)


if __name__ == "__main__":
    unittest.main()

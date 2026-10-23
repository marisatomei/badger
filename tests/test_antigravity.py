"""Host-side checks for the standalone October 2026 Antigravity app."""

import gc
import hashlib
import json
from pathlib import Path
import random
import sys
import types
import unittest
from unittest.mock import Mock
import weakref

from PIL import Image

import test_copilot


APP = Path(__file__).resolve().parents[1] / "badge/apps/Antigravity"
sys.path.insert(0, str(APP))
PERIOD = 1 << 30


class AntigravityTests(unittest.TestCase):
    def setUp(self):
        self.clock = test_copilot.Clock()
        self.keys = set()
        self.screen = Mock()
        self.screen.measure_text.side_effect = lambda text, *args: (len(text) * 7, 13)
        self.badge = Mock()
        self.badge.pressed.side_effect = lambda key: key in self.keys
        self.image = Mock()
        self.image.load.side_effect = lambda path: types.SimpleNamespace(width=192, height=180)
        self.namespace = {
            "badge": self.badge, "screen": self.screen,
            "color": Mock(), "font": Mock(), "image": self.image,
            "rect": lambda *args: args, "HIRES": 1, "VSYNC": 2,
        }
        for key in ("BACK", "LEFT", "RIGHT", "UP", "DOWN", "SELECT"):
            self.namespace["BUTTON_" + key] = key
        source = (APP / "__init__.py").read_text(encoding="utf-8").split("\napp = AntigravityApp()")[0]
        exec(compile(source, str(APP / "__init__.py"), "exec"), self.namespace)
        self.namespace["time"] = self.clock
        self.namespace["random"] = random.Random(42)
        self.app = self.namespace["AntigravityApp"](monitor=False)

    def press(self, key):
        self.keys.add(key)
        try:
            return self.app.update()
        finally:
            self.keys.clear()

    def labels(self):
        return [call.args[0] for call in self.screen.text.call_args_list]

    def test_native_runtime_and_initial_offline_render(self):
        self.app.update()
        self.badge.mode.assert_called_once_with(3)
        self.image.load.assert_called_once_with("/system/apps/Antigravity/assets/neutral.png")
        self.screen.blit.assert_called_once_with(self.app.sprite, (64, 22, 192, 180))
        self.assertIn("Google Antigravity", self.labels())
        self.assertIn("Antigravity Agent", self.labels())

    def test_back_exits_from_every_mode_and_error(self):
        for mode in ("idle", "working", "attention", "complete", "surprise", "sleep"):
            self.app.set_mode(mode, self.clock.now)
            self.assertIs(self.press("BACK"), False)
        self.app.error = "Missing or invalid artwork"
        self.assertIs(self.press("BACK"), False)

    def test_standalone_entry_point_runs_and_cleans_up_on_exit(self):
        self.keys.add("BACK")
        run = Mock(side_effect=lambda update: self.assertIs(update(), False))
        self.namespace["run"] = run
        source = (APP / "__init__.py").read_text(encoding="utf-8")
        exec("\napp = AntigravityApp()" + source.split("\napp = AntigravityApp()")[1], self.namespace)
        run.assert_called_once_with(self.namespace["app"].update)
        self.assertIsNone(self.namespace["app"].sprite)

    def test_idle_blink_sequence_and_next_deadline(self):
        self.app.next_look = self.clock.ticks_add(self.clock.now, 10000)
        self.clock.now = self.app.next_blink
        for expected in (1, 2, 3, 4, 3, 2, 1):
            self.app.update()
            self.assertEqual(self.app.sprite_name, "blink-%d" % expected)
            self.clock.advance(45)
        self.app.update()
        self.assertEqual(self.app.sprite_name, "neutral")

    def test_all_runtime_frame_names_exist_and_have_bounded_dimensions(self):
        expected = {"neutral", "blink-1", "blink-2", "blink-3", "blink-4"}
        for track in (*self.namespace["LOOKS"], "surprise", "working", "attention", "complete"):
            expected.update("%s-%02d" % (track, index) for index in range(12))
        assets = APP / "assets"
        self.assertEqual({path.stem for path in assets.glob("*.png")}, expected)
        for name in expected:
            with Image.open(assets / (name + ".png")) as frame:
                self.assertEqual(frame.size, (192, 180))
                self.assertEqual(frame.mode, "RGB")
                frame.verify()
            with Image.open(assets / (name + ".png")) as frame:
                bounds = frame.point(lambda value: 255 if value > 16 else 0).getbbox()
                self.assertLess(bounds[3] + 22, 194)
        with Image.open(APP / "icon.png") as icon:
            self.assertEqual(icon.size, (24, 24))
            self.assertEqual(icon.mode, "RGB")
        self.assertLess(sum(path.stat().st_size for path in assets.iterdir()), 3_000_000)

    def test_source_metadata_and_mit_license_ship_with_assets(self):
        assets = APP / "assets"
        metadata = json.loads((assets / "sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(metadata["files"]), 101)
        for entry in metadata["files"]:
            self.assertEqual(hashlib.sha256((assets / entry["file"]).read_bytes()).hexdigest(),
                             entry["sha256"])
        license_text = (assets / "LICENSE.txt").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)


if __name__ == "__main__":
    unittest.main()

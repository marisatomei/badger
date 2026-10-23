"""Tests for the Antigravity desktop bridge."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

BRIDGE_DIR = Path(__file__).resolve().parents[1] / "tools/antigravity_bridge"
sys.path.insert(0, str(BRIDGE_DIR))

import antigravity_bridge as bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.test_cfg = {
            "host": "127.0.0.1",
            "port": 80,
            "deviceId": "0123456789abcdef",
            "token": "abcdef0123456789abcdef0123456789"
        }
        bridge.save_config(self.test_cfg, self.config_path)

    def test_load_and_save_config(self):
        loaded, path = bridge.load_config(self.config_path)
        self.assertEqual(loaded["deviceId"], self.test_cfg["deviceId"])
        self.assertEqual(loaded["token"], self.test_cfg["token"])

    @patch("urllib.request.urlopen")
    def test_post_badge_state(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status, res = bridge.post_badge("/state", "working\n", self.test_cfg)
        self.assertEqual(status, 200)
        self.assertEqual(res, {"ok": True})

    @patch("urllib.request.urlopen")
    def test_get_status(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"protocol": 8, "character": "antigravity"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        status, res = bridge.get_status(self.test_cfg)
        self.assertEqual(status, 200)
        self.assertEqual(res["character"], "antigravity")

    @patch("urllib.request.urlopen")
    def test_hook_pre_invocation(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        args = MagicMock()
        args.hook_type = "pre_invocation"
        args.read_stdin = False
        ret = bridge.cmd_hook(args, self.test_cfg)
        self.assertEqual(ret, 0)

    @patch("urllib.request.urlopen")
    def test_hook_pre_tool_use_with_payload(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        args = MagicMock()
        args.hook_type = "pre_tool_use"
        args.read_stdin = False
        payload = json.dumps({"toolCall": {"name": "run_command"}})
        ret = bridge.cmd_hook(args, self.test_cfg, input_data=payload)
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()

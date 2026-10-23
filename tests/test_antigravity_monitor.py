"""Antigravity wire compatibility, bounded networking, and protocol endpoints."""

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_copilot

APP = Path(__file__).resolve().parents[1] / "badge/apps/Antigravity"
sys.path.insert(0, str(APP))
import antigravity_monitor as monitor


class AntigravityProtocolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.clock = test_copilot.Clock()
        patcher = patch.object(monitor, "time", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = str(Path(self.directory.name) / "pairing.json")
        self.protocol = monitor.Protocol(self.path)
        self.protocol.open_pairing(self.clock.now)
        code, paired = self.request("POST", "/pair", self.protocol.pairing_code)
        self.assertEqual(code, 200)
        self.token = paired["token"]

    def request(self, method, path, body="", authenticated=False):
        headers = {"authorization": "Bearer " + self.token} if authenticated else {}
        return self.protocol.handle(method, path, headers, body.encode(), self.clock.now)

    def test_pairing_is_physical_single_use_and_persisted(self):
        self.assertIsNone(self.protocol.pairing_code)
        self.assertEqual(self.request("POST", "/pair", "12345678")[0], 403)
        restored = monitor.Protocol(self.path)
        self.assertEqual(restored.token, self.token)
        self.assertEqual(restored.device_id, self.protocol.device_id)
        self.assertTrue(monitor.valid_hex(restored.device_id, 16))
        self.assertTrue(monitor.valid_hex(restored.token, 32))

    def test_protocol_negotiation_reports_antigravity(self):
        status, value = self.request("GET", "/status", authenticated=True)
        self.assertEqual(status, 200)
        self.assertEqual(value["protocol"], 8)
        self.assertEqual(value["character"], "antigravity")
        self.assertEqual(value["board"], "github-universe-2026")
        self.assertIsInstance(value["boot"], int)

    def test_states_and_invalid_packets(self):
        for state in monitor.STATES:
            self.assertEqual(self.request("POST", "/state", state, True)[0], 200)
            self.assertEqual(self.protocol.state, state)
            self.assertTrue(self.protocol.live(self.clock.now))
        for value in ("!working", '{"state":"working"}', "invalid_state", ""):
            self.assertEqual(self.request("POST", "/state", value, True)[0], 400)

    def test_icon_agents_and_usage_packets(self):
        mask = bytes([128] + [0] * 71)
        packet = "%antigravity:4285f4:" + base64.b64encode(mask).decode() + "\n"
        self.assertEqual(self.request("POST", "/icon", packet, True)[0], 200)
        self.assertEqual(self.protocol.icons["antigravity"], ((66, 133, 244), mask))

        self.assertEqual(self.request("POST", "/agents", "&antigravity=w,linter=a\n", True)[0], 200)
        self.assertEqual(self.protocol.agents, [("antigravity", "w"), ("linter", "a")])

        self.assertEqual(self.request("POST", "/usage", "$AIC: 42|Tokens: 1.5M\n", True)[0], 200)
        self.assertEqual(self.protocol.usage, ["AIC: 42", "Tokens: 1.5M"])


if __name__ == "__main__":
    unittest.main()

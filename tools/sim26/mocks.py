"""Persistent State and mock hardware/firmware modules for the 2026 simulator."""

from __future__ import annotations

import builtins
import gc
import json
import math
import sys
import time
import urllib.request
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pygame

from sim26.primitives import ColorObj, color, shape
from sim26.screen import FontWrapper, Screen
from sim26.vfs import BADGE_ROOT, STATE_DIR, map_system_path

# -----------------------------------------------------------------------------
# Persistent State
# -----------------------------------------------------------------------------


class State:
    @staticmethod
    def load(name: str, state_dict: dict) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / f"{name}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    state_dict.update(data)
            except Exception:
                pass

    @staticmethod
    def save(name: str, state_dict: dict) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / f"{name}.json"
        try:
            path.write_text(json.dumps(state_dict, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def delete(name: str) -> None:
        path = STATE_DIR / f"{name}.json"
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Mock Hardware Modules
# -----------------------------------------------------------------------------


def install_mock_modules() -> None:
    # display
    m_display = ModuleType("display")
    m_display.set_async = lambda *args, **kwargs: None
    m_display.update = lambda *args, **kwargs: None
    m_display.backlight = lambda *args, **kwargs: None
    m_display.brightness = lambda *args, **kwargs: None
    sys.modules["display"] = m_display

    # easing
    m_easing = ModuleType("easing")
    m_easing.easeOutCubic = lambda t: 1.0 - (1.0 - max(0.0, min(1.0, float(t)))) ** 3
    m_easing.easeInOutCubic = lambda t: 4.0 * t**3 if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
    c1 = 1.70158
    c3 = c1 + 1.0
    m_easing.easeOutBack = lambda t: 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)
    m_easing.easeOutElastic = (
        lambda t: 0.0
        if t <= 0
        else (1.0 if t >= 1 else 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * (2.0 * math.pi) / 3.0) + 1.0)
    )
    sys.modules["easing"] = m_easing

    # badgeware
    m_badgeware = ModuleType("badgeware")
    m_badgeware.__path__ = []
    m_badgeware.State = State
    m_badgeware.display = m_display
    m_badgeware.get_backlight = lambda: 1.0
    m_badgeware.set_backlight = lambda level: None
    m_badgeware.get_battery_level = lambda: 100
    m_badgeware.is_charging = lambda: False
    m_badgeware.fatal_error = lambda msg: print(f"Fatal error: {msg}")

    # Legacy badgeware compatibility for apps like 'system'
    class LegacyIO:
        BUTTON_A = "A"
        BUTTON_B = "B"
        BUTTON_C = "C"
        BUTTON_UP = "UP"
        BUTTON_DOWN = "DOWN"
        pressed = set()

    m_badgeware.io = LegacyIO
    m_badgeware.brushes = SimpleNamespace(color=lambda r, g, b, a=255: ColorObj(r, g, b, a))
    m_badgeware.shapes = shape
    m_badgeware.screen = Screen(160, 120)
    m_badgeware.PixelFont = SimpleNamespace(load=lambda path: FontWrapper("pixel", 12))
    m_badgeware.run = lambda update_fn: None

    # badgeware.ir & link
    m_badgeware_ir = ModuleType("badgeware.ir")

    class IRMock:
        def bind(self, descriptor):
            return descriptor

        def close(self):
            pass

    m_badgeware_ir.ir = IRMock()
    m_badgeware.ir = m_badgeware_ir
    sys.modules["badgeware.ir"] = m_badgeware_ir

    class MockLink:
        def __init__(self, game):
            self.id = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0"
            self.name = "My Badge"
            self.partner = None
            self.linked = False
            self.central = True
            self.journal = None

        def capacity(self):
            return 256

        def leave(self):
            pass

        def close(self):
            pass

        def pump(self):
            pass

        def update(self):
            pass

        def receive(self):
            return []

        def send(self, data):
            return True

    class MockProximity:
        cooldown_ms = 5000

        def __init__(self, link):
            self.cooldown_ms = 5000
            self.sync_id = None

        def rest(self, *args):
            pass

        def clear(self):
            pass

        def lights(self, now):
            return None

        def update(self, now):
            pass

        def syncing(self):
            return None

        def cooling(self, now):
            return None

        def progress(self, now):
            return 0.0

    class MockBadgeLink:
        ID_LEN = 8
        Link = MockLink
        Proximity = MockProximity

        def badge_id_hex(self, badge_id):
            if isinstance(badge_id, (bytes, bytearray)):
                return badge_id.hex()
            return str(badge_id)

        def draw_identicon(self, scr, badge_id, x, y, size, *args):
            avatar_path = STATE_DIR / "badge_avatar.png"
            if badge_id == b"\x12\x34\x56\x78\x9a\xbc\xde\xf0" and avatar_path.exists():
                try:
                    surf = pygame.image.load(str(avatar_path)).convert_alpha()
                    scaled = pygame.transform.smoothscale(surf, (int(size), int(size)))
                    scr._surface.blit(scaled, (int(x), int(y)))
                    return
                except Exception:
                    pass
            raw = list(badge_id) if isinstance(badge_id, (bytes, bytearray)) else [ord(ch) for ch in str(badge_id)]
            while len(raw) < 8:
                raw.append(0)
            bg = ((raw[0] * 37) % 50 + 15, (raw[1] * 41) % 50 + 15, (raw[2] * 43) % 50 + 25)
            fg = ((raw[3] * 53) % 160 + 90, (raw[4] * 59) % 160 + 90, (raw[5] * 61) % 160 + 90)
            pygame.draw.rect(scr._surface, bg, pygame.Rect(x, y, size, size), border_radius=4)
            cell = size / 5.0
            bits = (raw[0] << 8) | raw[1]
            for row in range(5):
                for col in range(3):
                    bit_index = row * 3 + col
                    if (bits >> bit_index) & 1:
                        for c in (col, 4 - col):
                            rect_cell = pygame.Rect(
                                int(x + c * cell), int(y + row * cell), int(cell) + 1, int(cell) + 1
                            )
                            pygame.draw.rect(scr._surface, fg, rect_cell)

        def identicon(self, badge_id):
            raw = list(badge_id) if isinstance(badge_id, (bytes, bytearray)) else [ord(ch) for ch in str(badge_id)]
            while len(raw) < 8:
                raw.append(0)
            bg = color.rgb((raw[0] * 37) % 50 + 15, (raw[1] * 41) % 50 + 15, (raw[2] * 43) % 50 + 25)
            fg = color.rgb((raw[3] * 53) % 160 + 90, (raw[4] * 59) % 160 + 90, (raw[5] * 61) % 160 + 90)
            return (bg, fg, bg)

    m_badgeware.link = MockBadgeLink()
    sys.modules["badgeware"] = m_badgeware

    # secrets (loaded before fetch/requests so fallback user data can read it)
    m_sec = ModuleType("secrets")
    sec_path = BADGE_ROOT / "secrets.py"
    if sec_path.exists():
        try:
            exec(sec_path.read_text(encoding="utf-8"), m_sec.__dict__)
        except Exception:
            pass
    sec_local = BADGE_ROOT / "secrets.local.py"
    if sec_local.exists():
        try:
            exec(sec_local.read_text(encoding="utf-8"), m_sec.__dict__)
        except Exception:
            pass
    m_sec.require = lambda *args: True
    m_sec.locked = lambda key: False
    m_sec.save = lambda d: None
    sys.modules["secrets"] = m_sec

    # fetch
    m_fetch = ModuleType("fetch")

    class MockRequest:
        def __init__(self, url, file):
            self.url = url
            self.file = file
            self.state = "Done"
            self.error = None

        def __bool__(self):
            return True

    class MockFetchUrl:
        def __init__(self, url, headers=None):
            self.url = url
            self.headers = headers

        def to(self, dest):
            resolved_dest = Path(map_system_path(dest))
            resolved_dest.parent.mkdir(parents=True, exist_ok=True)
            fetched = False
            urls_to_try = [self.url]
            if "wsrv.nl/?url=https://github.com/" in self.url:
                gh_png = self.url.split("url=")[-1].split("&")[0]
                urls_to_try.append(f"{gh_png}?size=150")
            for candidate_url in urls_to_try:
                try:
                    req = urllib.request.Request(
                        candidate_url, headers=self.headers or {"User-Agent": "GitHub Universe Badge 2026"}
                    )
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        if resp.status == 200:
                            resolved_dest.write_bytes(resp.read())
                            fetched = True
                            break
                except Exception:
                    fetched = False
            if not fetched and not resolved_dest.exists():
                if "badge_user.json" in str(dest):
                    handle_name = getattr(m_sec, "GITHUB_USERNAME", "mgliot") or "mgliot"
                    contact_name = getattr(m_sec, "CONTACT_NAME", "Marcelino Gonzalez") or "Marcelino Gonzalez"
                    resolved_dest.write_text(
                        json.dumps(
                            {
                                "login": handle_name,
                                "name": contact_name,
                                "followers": 18,
                                "public_repos": 12,
                            }
                        ),
                        encoding="utf-8",
                    )
                elif "badge_contribs.json" in str(dest):
                    weeks = []
                    for w in range(52):
                        days = [{"level": (w + d) % 4} for d in range(7)]
                        weeks.append({"contribution_days": days})
                    resolved_dest.write_text(
                        json.dumps({"total_contributions": 342, "weeks": weeks}),
                        encoding="utf-8",
                    )
                elif "badge_avatar.png" in str(dest):
                    surf = pygame.Surface((80, 80), pygame.SRCALPHA)
                    surf.fill((88, 58, 247, 255))
                    pygame.image.save(surf, str(resolved_dest))
                else:
                    resolved_dest.touch()
            return MockRequest(self.url, dest)

    class AsyncFetch:
        MAX_HEADER_BYTES = 8192

    m_fetch.AsyncFetch = AsyncFetch
    m_fetch.url = lambda u, headers=None: MockFetchUrl(u, headers)
    sys.modules["fetch"] = m_fetch

    # pairing
    m_pairing = ModuleType("pairing")

    class Pairing:
        def __init__(self, x=0, y=0, unit=1):
            pass

        def draw_together(self, now):
            pass

        def draw_apart(self):
            pass

        def draw_loop(self, now):
            pass

    m_pairing.Pairing = Pairing
    sys.modules["pairing"] = m_pairing

    # hints
    m_hints = ModuleType("hints")

    class HintStyle:
        def __init__(self, fg, dim, bg):
            pass

    m_hints.Style = HintStyle
    m_hints.hint_width = lambda *args: 20
    m_hints.hint_height = lambda *args: 20
    m_hints.draw_hint = lambda *args: None
    m_hints.flipped = lambda: False
    sys.modules["hints"] = m_hints

    # missing_details
    m_md = ModuleType("missing_details")
    m_md.mona_sans = lambda: FontWrapper("mona_sans", 16)
    m_md.missing = lambda key: []

    def _md_show(missing, draw_graph, message_tuple):
        if draw_graph:
            draw_graph()
        scr = getattr(builtins, "screen", None)
        if scr is not None:
            scr.pen = color.rgb(255, 255, 255)
            for i, line in enumerate(message_tuple):
                scr.text(line, 20, 40 + i * 20)

    m_md.show = _md_show
    sys.modules["missing_details"] = m_md

    # machine
    m_machine = ModuleType("machine")

    class Pin:
        IRQ_FALLING = 1
        IRQ_RISING = 2

        class board:
            BUTTON_HOME = None
            BUTTON_UP = None
            BUTTON_DOWN = None
            BUTTON_LEFT = None
            BUTTON_RIGHT = None
            BUTTON_SELECT = None
            BUTTON_BACK = None
            BUTTON_MENU = None

        def __init__(self, *args, **kwargs):
            pass

        def irq(self, *args, **kwargs):
            pass

    for attr in [
        "BUTTON_HOME",
        "BUTTON_UP",
        "BUTTON_DOWN",
        "BUTTON_LEFT",
        "BUTTON_RIGHT",
        "BUTTON_SELECT",
        "BUTTON_BACK",
        "BUTTON_MENU",
    ]:
        setattr(Pin.board, attr, Pin())

    class RTC:
        def datetime(self):
            now = time.localtime()
            return (now.tm_year, now.tm_mon, now.tm_mday, now.tm_wday, now.tm_hour, now.tm_min, now.tm_sec, 0)

    m_machine.Pin = Pin
    m_machine.RTC = RTC
    m_machine.PWRON_RESET = 1
    m_machine.HARD_RESET = 2
    m_machine.WDT_RESET = 3
    m_machine.DEEPSLEEP_RESET = 4
    m_machine.SOFT_RESET = 5
    m_machine.reset_cause = lambda: 1
    m_machine.unique_id = lambda: b"\x12\x34\x56\x78\x9a\xbc\xde\xf0"
    sys.modules["machine"] = m_machine

    # brand
    m_brand = ModuleType("brand")
    m_brand.GREY_0 = ColorObj(250, 250, 250)
    m_brand.GRAY_0 = m_brand.GREY_0
    m_brand.LIGHT_GREY = ColorObj(220, 220, 220)
    m_brand.GRAY_1 = ColorObj(240, 240, 240)
    m_brand.GRAY_2 = ColorObj(200, 200, 200)
    m_brand.GRAY_3 = ColorObj(150, 150, 150)
    m_brand.GRAY_4 = ColorObj(100, 100, 100)
    m_brand.GRAY_5 = ColorObj(60, 60, 60)
    m_brand.GRAY_6 = ColorObj(25, 25, 25)
    m_brand.GREEN_1 = ColorObj(50, 200, 100)
    m_brand.GREEN_2 = ColorObj(40, 160, 80)
    m_brand.GREEN_3 = ColorObj(30, 120, 60)
    m_brand.GREEN_4 = ColorObj(20, 80, 40)
    m_brand.ORANGE_2 = ColorObj(255, 140, 40)
    m_brand.BLACK = ColorObj(0, 0, 0)
    m_brand.WHITE = ColorObj(255, 255, 255)
    sys.modules["brand"] = m_brand

    # gc & micropython
    gc.mem_free = lambda: 512000  # type: ignore

    m_mp = ModuleType("micropython")
    m_mp.const = lambda x: x
    m_mp.native = lambda f: f
    m_mp.viper = lambda f: f
    m_mp.mem_info = lambda *args: None
    sys.modules["micropython"] = m_mp
    builtins.micropython = m_mp  # type: ignore

    # wifi & ntptime & utime
    _orig_time = getattr(time, "_orig_time", time.time)
    time._orig_time = _orig_time  # type: ignore
    time.time = lambda: int(_orig_time())  # type: ignore
    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(time.monotonic() * 1000) & 0x3FFFFFFF  # type: ignore
        time.ticks_diff = lambda a, b: ((a - b + 0x20000000) & 0x3FFFFFFF) - 0x20000000  # type: ignore
        time.ticks_add = lambda a, b: (a + b) & 0x3FFFFFFF  # type: ignore
        time.sleep_ms = lambda ms: time.sleep(max(0.0, ms / 1000.0))  # type: ignore
    sys.modules["utime"] = time

    m_wifi = ModuleType("wifi")
    m_wifi.is_connected = lambda: True
    m_wifi.connect = lambda *args, **kwargs: True
    m_wifi.disconnect = lambda: True
    m_wifi.failure = lambda: False
    m_wifi.status = lambda: (3, "connected")
    sys.modules["wifi"] = m_wifi

    m_net = ModuleType("network")
    m_net.STA_IF = 0
    m_net.AP_IF = 1

    class MockWLAN:
        def __init__(self, interface=0):
            self.interface = interface
            self._active = True
            self._connected = True

        def active(self, is_active=None):
            if is_active is not None:
                self._active = bool(is_active)
            return self._active

        def connect(self, ssid=None, password=None):
            self._connected = True

        def disconnect(self):
            self._connected = False

        def isconnected(self):
            return self._connected

        def status(self):
            return 3

        def ifconfig(self, config=None):
            return ("192.168.1.100", "255.255.255.0", "192.168.1.1", "8.8.8.8")

    m_net.WLAN = lambda interface=0: MockWLAN(interface)
    sys.modules["network"] = m_net

    m_ntp = ModuleType("ntptime")
    m_ntp.settime = lambda: None
    sys.modules["ntptime"] = m_ntp

    # requests with live HTTP fetching and graceful offline mock fallback
    m_req = ModuleType("requests")

    class SimulatorResponse:
        def __init__(self, status_code: int, content: bytes, text: str, data: Any = None):
            self.status_code = status_code
            self.content = content
            self.text = text
            self._data = data
            self.ok = 200 <= status_code < 400

        def json(self) -> Any:
            if self._data is not None:
                return self._data
            if self.text:
                try:
                    return json.loads(self.text)
                except Exception:
                    pass
            return {}

        def close(self) -> None:
            pass

    def _sim_request(url: str, *args, **kwargs) -> SimulatorResponse:
        headers = kwargs.get("headers") or {"User-Agent": "GitHub Universe Badge 2026"}
        timeout = kwargs.get("timeout") or 5.0
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read()
                text = content.decode("utf-8", errors="replace")
                return SimulatorResponse(resp.status, content, text)
        except Exception:
            pass

        # Offline / fallback responses for known endpoints
        now = int(time.time())
        if "wheretheiss.at" in url and "positions" in url:
            stamps = [now]
            if "timestamps=" in url:
                stamps_str = url.split("timestamps=")[-1].split("&")[0]
                stamps = [int(s) for s in stamps_str.split(",") if s.isdigit()]
            points = []
            for ts in stamps:
                points.append(
                    {
                        "name": "iss",
                        "id": 25544,
                        "latitude": 25.0 + 20.0 * math.sin(ts / 900.0),
                        "longitude": ((ts % 5400) / 5400.0 * 360.0) - 180.0,
                        "altitude": 420.0,
                        "velocity": 27600.0,
                        "visibility": "daylight",
                        "footprint": 4500.0,
                        "solar_lat": -10.0,
                        "solar_lon": 10.0,
                        "timestamp": ts,
                    }
                )
            raw = json.dumps(points)
            return SimulatorResponse(200, raw.encode("utf-8"), raw, points)

        if "wheretheiss.at" in url:
            data = {
                "name": "iss",
                "id": 25544,
                "latitude": 20.5,
                "longitude": -15.2,
                "altitude": 423.5,
                "velocity": 27570.0,
                "visibility": "daylight",
                "footprint": 4520.0,
                "solar_lat": -11.5,
                "solar_lon": 9.5,
                "timestamp": now,
            }
            raw = json.dumps(data)
            return SimulatorResponse(200, raw.encode("utf-8"), raw, data)

        if "api.github.com/users/" in url:
            handle = getattr(m_sec, "GITHUB_USERNAME", "mgliot") or "mgliot"
            name = getattr(m_sec, "CONTACT_NAME", "Marcelino Gonzalez") or "Marcelino Gonzalez"
            data = {
                "login": handle,
                "name": name,
                "followers": 18,
                "public_repos": 12,
            }
            raw = json.dumps(data)
            return SimulatorResponse(200, raw.encode("utf-8"), raw, data)

        return SimulatorResponse(200, b"{}", "{}")

    m_req.get = _sim_request
    m_req.post = _sim_request
    sys.modules["requests"] = m_req

    # powman
    m_powman = ModuleType("powman")
    m_powman.WAKE_POWER = 1
    m_powman.WAKE_WATCHDOG = 2
    m_powman.WAKE_DOUBLETAP = 3
    m_powman.get_wake_reason = lambda: m_powman.WAKE_POWER
    m_powman.reset_into_msc = lambda: None
    sys.modules["powman"] = m_powman

    # sparkle
    m_sparkle = ModuleType("sparkle")
    m_sparkle.request_local_show = lambda: True
    m_sparkle.resume = lambda: None
    m_sparkle.pause = lambda: None
    m_sparkle.stop = lambda: None
    sys.modules["sparkle"] = m_sparkle

    # sensor breakout mocks (sense app)
    m_machine.I2C = lambda *args, **kwargs: None
    m_bme = ModuleType("breakout_bme280")
    m_bme.BreakoutBME280 = lambda *args, **kwargs: SimpleNamespace(read=lambda: (22.5, 101325.0, 45.0))
    sys.modules["breakout_bme280"] = m_bme

    m_ltr = ModuleType("breakout_ltr559")
    m_ltr.BreakoutLTR559 = lambda *args, **kwargs: SimpleNamespace(get_reading=lambda: (0, 0, 0, 0, 0, 0, 120.0))
    sys.modules["breakout_ltr559"] = m_ltr

    m_lsm = ModuleType("lsm6ds3")
    m_lsm.NORMAL_MODE_104HZ = 1
    m_lsm.LSM6DS3 = lambda *args, **kwargs: SimpleNamespace(get_readings=lambda: (0.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    sys.modules["lsm6ds3"] = m_lsm

    # aye_arr.nec & remotes
    m_ayearr = ModuleType("aye_arr")
    m_ayearr.__path__ = []
    m_nec = ModuleType("aye_arr.nec")
    m_nec.__path__ = []

    class NECReceiver:
        def __init__(self, *args, **kwargs):
            pass

        def bind(self, descriptor):
            return descriptor

        def start(self):
            pass

        def stop(self):
            pass

        def decode(self):
            return False

        def read(self):
            return None

    m_nec.NECReceiver = NECReceiver

    m_remotes = ModuleType("aye_arr.nec.remotes")
    m_remotes.__path__ = []

    m_desc = ModuleType("aye_arr.nec.remotes.descriptor")

    class RemoteDescriptor:
        NAME = "Unknown"
        ADDRESS = 0x00
        BUTTON_CODES = {}

        def __init__(self):
            self._buttons = {}
            self.on_known = None
            self.on_any = None

        def bind(self, name, on_press, on_repeat=True, on_release=False):
            pass

        def bind_code(self, code, on_press, on_repeat=True, on_release=False):
            pass

    m_desc.RemoteDescriptor = RemoteDescriptor
    m_remotes.descriptor = m_desc
    m_nec.remotes = m_remotes
    m_ayearr.nec = m_nec

    sys.modules["aye_arr"] = m_ayearr
    sys.modules["aye_arr.nec"] = m_nec
    sys.modules["aye_arr.nec.remotes"] = m_remotes
    sys.modules["aye_arr.nec.remotes.descriptor"] = m_desc

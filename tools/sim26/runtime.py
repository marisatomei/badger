"""Input constants, BadgeRuntime, DisplayMock, and SimulatorApp lifecycle."""

from __future__ import annotations

import builtins
import importlib.util
import math
import os
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pygame

from sim26.primitives import brush, color, mat3, rect, shape, vec2
from sim26.screen import Image, Screen, font, image
from sim26.vfs import APPS_DIR, BADGE_ROOT, REPO_ROOT, map_system_path

# -----------------------------------------------------------------------------
# Input Constants & Badge Runtime
# -----------------------------------------------------------------------------

_active_badge_runtime: Any = None
_active_sim_app: Any = None


class Button(str):
    def value(self) -> int:
        if _active_badge_runtime and self in _active_badge_runtime._current_keys:
            return 0
        return 1


BUTTON_UP = Button("UP")
BUTTON_DOWN = Button("DOWN")
BUTTON_LEFT = Button("LEFT")
BUTTON_RIGHT = Button("RIGHT")
BUTTON_SELECT = Button("SELECT")
BUTTON_BACK = Button("BACK")
BUTTON_MENU = Button("MENU")
BUTTON_HOME = Button("HOME")

HIRES = 1
LORES = 0
VSYNC = 2
ELLIPSES = 1

KEY_MAP = {
    pygame.K_UP: BUTTON_UP,
    pygame.K_w: BUTTON_UP,
    pygame.K_DOWN: BUTTON_DOWN,
    pygame.K_s: BUTTON_DOWN,
    pygame.K_LEFT: BUTTON_LEFT,
    pygame.K_a: BUTTON_LEFT,
    pygame.K_RIGHT: BUTTON_RIGHT,
    pygame.K_d: BUTTON_RIGHT,
    pygame.K_RETURN: BUTTON_SELECT,
    pygame.K_SPACE: BUTTON_SELECT,
    pygame.K_z: BUTTON_SELECT,
    pygame.K_ESCAPE: BUTTON_BACK,
    pygame.K_BACKSPACE: BUTTON_BACK,
    pygame.K_x: BUTTON_BACK,
    pygame.K_TAB: BUTTON_MENU,
    pygame.K_m: BUTTON_MENU,
    pygame.K_h: BUTTON_HOME,
}


class ButtonGroup:
    def __init__(self, runtime: BadgeRuntime, allowed: set[str] | None = None):
        self._runtime = runtime
        self._allowed = allowed

    def pressed(self, action: str | None = None) -> bool | set[str]:
        if action is not None:
            return self._runtime.pressed(action)
        p = self._runtime.pressed()
        if isinstance(p, set):
            return (p & self._allowed) if self._allowed is not None else set(p)
        return bool(p)

    def held(self, action: str | None = None) -> bool | set[str]:
        if action is not None:
            return self._runtime.held(action)
        h = self._runtime.held()
        if isinstance(h, set):
            return (h & self._allowed) if self._allowed is not None else set(h)
        return bool(h)

    def released(self, action: str | None = None) -> bool | set[str]:
        if action is not None:
            return self._runtime.released(action)
        r = self._runtime.released()
        if isinstance(r, set):
            return (r & self._allowed) if self._allowed is not None else set(r)
        return bool(r)

    def touched(self, action: str | None = None) -> bool | set[str]:
        if action is not None:
            return self._runtime.touched(action)
        t = self._runtime.touched()
        if isinstance(t, set):
            return (t & self._allowed) if self._allowed is not None else set(t)
        return bool(t)


class BadgeRuntime:
    def __init__(self, screen_ref: Screen):
        global _active_badge_runtime
        _active_badge_runtime = self
        self.screen_ref = screen_ref
        self.ticks = 0
        self.ticks_delta = 16
        self.default_clear: Any = None
        self._upside_down = False

        self._current_keys: set[str] = set()
        self._pressed_this_frame: set[str] = set()
        self._released_this_frame: set[str] = set()
        self._touched_keys: set[str] = set()
        self._back_checked: bool = False

        PAD_BUTTONS = {BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT}
        FACE_BUTTONS = {BUTTON_SELECT, BUTTON_BACK, BUTTON_HOME, BUTTON_MENU}
        self.pad = ButtonGroup(self, PAD_BUTTONS)
        self.buttons = ButtonGroup(self, FACE_BUTTONS)
        self.all = ButtonGroup(self, None)

    def is_charging(self) -> bool:
        return False

    def battery(self) -> float:
        return 85.0

    def battery_level(self) -> int:
        return 85

    def is_battery(self) -> bool:
        return True

    def mode(self, m: int) -> None:
        if m & HIRES:
            self.screen_ref._resize(320, 240)
        else:
            self.screen_ref._resize(160, 120)

    def upside_down(self) -> bool:
        return self._upside_down

    def rotate_180(self, enabled: bool | None = None) -> bool:
        if enabled is not None:
            self._upside_down = bool(enabled)
        return self._upside_down

    def autorotate(self, enabled: bool | None = None) -> bool:
        if enabled is not None:
            self._autorotate = bool(enabled)
        return getattr(self, "_autorotate", True)

    def pressed(self, action: str | None = None) -> bool | set[str]:
        if action == BUTTON_BACK:
            self._back_checked = True
        if action is None:
            return set(self._pressed_this_frame)
        return action in self._pressed_this_frame

    def held(self, action: str | None = None) -> bool | set[str]:
        if action == BUTTON_BACK:
            self._back_checked = True
        if action is None:
            return set(self._current_keys)
        return action in self._current_keys

    def released(self, action: str | None = None) -> bool | set[str]:
        if action == BUTTON_BACK:
            self._back_checked = True
        if action is None:
            return set(self._released_this_frame)
        return action in self._released_this_frame

    def touched(self, action: str | None = None) -> bool | set[str]:
        if action == BUTTON_BACK:
            self._back_checked = True
        if action is None:
            return set(self._touched_keys)
        return action in self._touched_keys

    def direction(self) -> vec2:
        dx = 0.0
        dy = 0.0
        if BUTTON_LEFT in self._current_keys:
            dx -= 1.0
        if BUTTON_RIGHT in self._current_keys:
            dx += 1.0
        if BUTTON_UP in self._current_keys:
            dy -= 1.0
        if BUTTON_DOWN in self._current_keys:
            dy += 1.0

        if dx != 0.0 and dy != 0.0:
            inv = 1.0 / math.sqrt(2.0)
            dx *= inv
            dy *= inv
        return vec2(dx, dy)

    def imu(self) -> tuple[float, float, float, float, float, float]:
        # Return mock accelerometer & gyro vectors
        return (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)

    def caselights(self, *args) -> tuple[float, float, float, float]:
        if not hasattr(self, "_caselights"):
            self._caselights = (0.0, 0.0, 0.0, 0.0)
        if len(args) == 1 and isinstance(args[0], (int, float)):
            v = float(args[0])
            self._caselights = (v, v, v, v)
        elif len(args) >= 4:
            self._caselights = (float(args[0]), float(args[1]), float(args[2]), float(args[3]))
        return self._caselights

    def poll(self) -> None:
        pass

    def update(self) -> None:
        if _active_sim_app is not None:
            _active_sim_app._tick_frame()


class DisplayMock:
    def set_async(self, async_mode: bool = True) -> None:
        pass

    def update(self) -> None:
        if _active_sim_app is not None:
            _active_sim_app._tick_frame()

    def backlight(self, level: float = 1.0) -> None:
        pass

    def brightness(self, level: float = 1.0) -> None:
        pass


# -----------------------------------------------------------------------------
# Runner & App Lifecycle
# -----------------------------------------------------------------------------


class RunResult:
    def __init__(self, result: Any = None):
        self.result = result


class SimulatorApp:
    def __init__(
        self,
        scale: int = 4,
        screenshots_dir: Path | None = None,
        perf: bool = False,
        max_frames: int | None = None,
        save_screenshot: Path | None = None,
    ):
        self.scale = scale
        self.screenshots_dir = screenshots_dir or (REPO_ROOT / "screenshots")
        self.perf = perf
        self.max_frames = max_frames
        self.frame_count = 0
        self.save_screenshot_path = save_screenshot

        pygame.init()
        pygame.display.set_caption("GitHub Universe 2026 Badge Simulator")

        self.screen_obj = Screen(160, 120)
        self.badge_obj = BadgeRuntime(self.screen_obj)

        self.window_surf: pygame.Surface | None = None
        self._update_window_size()

        self.clock = pygame.time.Clock()
        self.running = True
        self.next_app_to_launch: str | None = None
        self._last_ticks = pygame.time.get_ticks()

        global _active_sim_app
        _active_sim_app = self

        # Expose globals into builtins
        self._inject_globals()

    def _update_window_size(self) -> None:
        target_w = self.screen_obj.width * self.scale
        target_h = self.screen_obj.height * self.scale
        self.window_surf = pygame.display.set_mode((target_w, target_h))

    def _inject_globals(self) -> None:
        builtins.badge = self.badge_obj  # type: ignore
        builtins.screen = self.screen_obj  # type: ignore
        builtins.image = image  # type: ignore
        builtins.font = font  # type: ignore
        builtins.color = color  # type: ignore
        builtins.shape = shape  # type: ignore
        builtins.brush = brush  # type: ignore
        builtins.vec2 = vec2  # type: ignore
        builtins.rect = rect  # type: ignore
        builtins.mat3 = mat3  # type: ignore

        builtins.BUTTON_UP = BUTTON_UP  # type: ignore
        builtins.BUTTON_DOWN = BUTTON_DOWN  # type: ignore
        builtins.BUTTON_LEFT = BUTTON_LEFT  # type: ignore
        builtins.BUTTON_RIGHT = BUTTON_RIGHT  # type: ignore
        builtins.BUTTON_SELECT = BUTTON_SELECT  # type: ignore
        builtins.BUTTON_BACK = BUTTON_BACK  # type: ignore
        builtins.BUTTON_MENU = BUTTON_MENU  # type: ignore
        builtins.BUTTON_HOME = BUTTON_HOME  # type: ignore

        builtins.HIRES = HIRES  # type: ignore
        builtins.LORES = LORES  # type: ignore
        builtins.VSYNC = VSYNC  # type: ignore
        builtins.ELLIPSES = ELLIPSES  # type: ignore
        builtins.CENTER = Image.CENTER  # type: ignore
        builtins.LEFT = Image.LEFT  # type: ignore
        builtins.RIGHT = Image.RIGHT  # type: ignore
        builtins.TOP = Image.TOP  # type: ignore
        builtins.BOTTOM = Image.BOTTOM  # type: ignore

        builtins.display = DisplayMock()  # type: ignore
        builtins.rtc = SimpleNamespace(
            datetime=lambda *args: (lambda t: (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, t.tm_wday))(
                time.localtime()
            )
        )  # type: ignore

        builtins.run = self.run  # type: ignore
        builtins.launch = self.launch  # type: ignore
        builtins.reset = self.reset  # type: ignore
        builtins.file_exists = lambda p: os.path.exists(map_system_path(p))  # type: ignore
        builtins.is_dir = lambda p: os.path.isdir(map_system_path(p))  # type: ignore
        builtins.clamp = lambda val, low, high: max(low, min(high, val))  # type: ignore
        _orig_range = getattr(builtins, "_orig_range", builtins.range)
        builtins._orig_range = _orig_range  # type: ignore
        builtins.range = lambda *a: _orig_range(*(int(x) if isinstance(x, float) else x for x in a))  # type: ignore
        builtins.ptr8 = lambda buf: memoryview(buf).cast("B")  # type: ignore
        builtins.ptr16 = lambda buf: memoryview(buf).cast("H")  # type: ignore
        builtins.ptr32 = lambda buf: memoryview(buf).cast("I")  # type: ignore
        if "micropython" in sys.modules:
            builtins.micropython = sys.modules["micropython"]  # type: ignore

    def save_screenshot(self) -> None:
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = self.screenshots_dir / f"screenshot_{timestamp}.png"
        pygame.image.save(self.screen_obj._surface, str(filename))
        print(f"[Screenshot] Saved native {self.screen_obj.width}x{self.screen_obj.height} to {filename}")

    def _tick_frame(self) -> None:
        if not self.running:
            raise SystemExit(0)

        if (
            BUTTON_BACK in self.badge_obj._pressed_this_frame
            and not self.badge_obj._back_checked
            and getattr(self, "current_app", "") != "menu"
        ):
            print("[Simulator] Back pressed. Returning to menu...")
            self.reset()

        # 1. Input processing
        self.badge_obj._pressed_this_frame.clear()
        self.badge_obj._released_this_frame.clear()
        self.badge_obj._back_checked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                raise SystemExit(0)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F12:
                    self.save_screenshot()
                    continue
                if event.key == pygame.K_r:
                    self.badge_obj._upside_down = not self.badge_obj._upside_down
                    print(f"[Orientation] Inverted: {self.badge_obj._upside_down}")
                    continue
                if event.key == pygame.K_h and getattr(self, "current_app", "") != "menu":
                    print("[Simulator] Home pressed. Returning to menu...")
                    self.reset()

                action = KEY_MAP.get(event.key)
                if action:
                    self.badge_obj._pressed_this_frame.add(action)
                    self.badge_obj._current_keys.add(action)
                    self.badge_obj._touched_keys.add(action)

            elif event.type == pygame.KEYUP:
                action = KEY_MAP.get(event.key)
                if action:
                    self.badge_obj._released_this_frame.add(action)
                    self.badge_obj._current_keys.discard(action)
                    self.badge_obj._touched_keys.discard(action)

        # 2. Timing
        now = pygame.time.get_ticks()
        self.badge_obj.ticks = now
        self.badge_obj.ticks_delta = max(1, now - getattr(self, "_last_ticks", now))
        self._last_ticks = now

        # 3. Blit to window
        cur_w, cur_h = self.screen_obj.width * self.scale, self.screen_obj.height * self.scale
        if self.window_surf.get_size() != (cur_w, cur_h):
            self._update_window_size()

        scaled = pygame.transform.scale(self.screen_obj._surface, (cur_w, cur_h))
        if self.badge_obj._upside_down:
            scaled = pygame.transform.rotate(scaled, 180)

        self.window_surf.blit(scaled, (0, 0))
        pygame.display.flip()

        # Target 60 FPS
        self.clock.tick(60)

        if self.perf and (now % 500 < 20):
            fps = self.clock.get_fps()
            print(
                f"[Perf] FPS: {fps:.1f} | Resolution: {self.screen_obj.width}x{self.screen_obj.height} | Frame: {self.badge_obj.ticks_delta}ms"
            )

        if self.max_frames is not None:
            self.frame_count += 1
            if self.frame_count >= self.max_frames:
                self.running = False
                if self.save_screenshot_path:
                    self.save_screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen_obj._surface, str(self.save_screenshot_path))
                    print(f"[Screenshot] Saved frame to {self.save_screenshot_path}")
                raise SystemExit(0)

    def run(self, update_fn: Callable[[], Any]) -> RunResult:
        """Main loop executed by apps."""
        result: Any = None

        while self.running:
            try:
                self._tick_frame()
            except SystemExit:
                break

            try:
                if self.badge_obj.default_clear is not None:
                    prev_clip = self.screen_obj._surface.get_clip()
                    self.screen_obj._surface.set_clip(None)
                    self.screen_obj.clear(self.badge_obj.default_clear)
                    self.screen_obj._surface.set_clip(prev_clip)
                ret = update_fn()
                if ret is not None:
                    result = ret
                    if isinstance(ret, str):
                        self.next_app_to_launch = ret
                    break
                if (
                    BUTTON_BACK in self.badge_obj._pressed_this_frame
                    and not self.badge_obj._back_checked
                    and getattr(self, "current_app", "") != "menu"
                ):
                    print("[Simulator] Back pressed. Returning to menu...")
                    self.reset()
            except SystemExit:
                break
            except Exception as e:
                print(f"[Simulator] Error in update(): {e}")
                traceback.print_exc()
                break

        if self.save_screenshot_path:
            self.save_screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.screen_obj._surface, str(self.save_screenshot_path))
            print(f"[Screenshot] Saved frame to {self.save_screenshot_path}")

        return RunResult(result)

    def launch(self, app_path: str) -> Any:
        mapped = map_system_path(app_path)
        p = Path(mapped)
        if not p.is_absolute():
            if (APPS_DIR / p).exists():
                p = APPS_DIR / p
            elif (REPO_ROOT / p).exists():
                p = REPO_ROOT / p
            elif (BADGE_ROOT / p).exists():
                p = BADGE_ROOT / p

        if p.is_dir():
            target_py = p / "__init__.py"
        else:
            target_py = p

        if not target_py.exists():
            print(f"[Simulator] Could not launch: {target_py} not found")
            return None

        app_name = target_py.parent.name
        app_dir = str(target_py.parent.resolve())
        apps_root = str(APPS_DIR.resolve())
        for mod_name, mod_obj in list(sys.modules.items()):
            mod_file = getattr(mod_obj, "__file__", None)
            if mod_file and str(Path(mod_file).resolve()).startswith(apps_root):
                sys.modules.pop(mod_name, None)
        sys.path[:] = [
            entry
            for entry in sys.path
            if not str(Path(map_system_path(entry)).resolve()).startswith(apps_root)
        ]
        sys.path.insert(0, app_dir)
        self.screen_obj.clip = None
        self.screen_obj.alpha = 255
        try:
            os.chdir(app_dir)
        except Exception:
            pass

        self.current_app = app_name
        pygame.display.set_caption(f"Universe 2026 Badge Simulator - {app_name}")
        print(f"[Simulator] Launching {app_name} ({target_py})")

        spec = importlib.util.spec_from_file_location("__main__", str(target_py.resolve()))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules["__main__"] = mod
            try:
                spec.loader.exec_module(mod)
            except SystemExit:
                pass
            except Exception as e:
                print(f"[Simulator] Crash in {app_name}: {e}")
                traceback.print_exc()

        return None

    def reset(self) -> None:
        print("[Simulator] Soft reset requested. Returning to menu...")
        m_machine = sys.modules.get("machine")
        if m_machine is not None:
            m_machine.reset_cause = lambda: m_machine.WDT_RESET
        self.badge_obj._pressed_this_frame.clear()
        self.badge_obj._current_keys.clear()
        self.badge_obj._released_this_frame.clear()
        self.badge_obj._touched_keys.clear()
        self.next_app_to_launch = "/system/apps/menu"
        raise SystemExit(0)

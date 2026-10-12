#!/usr/bin/env python3
"""GitHub Universe 2026 Badge Simulator.

Runs Universe 2026 badge applications locally via Pygame by simulating the
2026 MicroPython runtime globals (badge, screen, image, font, color, shape,
brush, vec2, rect, mat3, run, button constants, display modes, and State).
"""

from __future__ import annotations

import argparse
import builtins
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
BADGE_ROOT = REPO_ROOT / "badge"
APPS_DIR = BADGE_ROOT / "apps"
STATE_DIR = REPO_ROOT / ".badge_state"

try:
    import pygame
except ImportError:
    # Auto-detect local virtual environment if active shell didn't activate it
    _venv_py = REPO_ROOT / ".venv" / "bin" / "python3"
    if _venv_py.exists() and Path(sys.executable).resolve() != _venv_py.resolve():
        os.execv(str(_venv_py), [str(_venv_py)] + sys.argv)
    raise SystemExit(
        "Pygame is required to run the Universe 2026 Badge Simulator.\n"
        "Run 'make setup' to set up the environment, or run: pip install pygame-ce"
    )

# -----------------------------------------------------------------------------
# Path Virtualization (/system -> badge)
# -----------------------------------------------------------------------------

def map_system_path(p: str | Path) -> str:
    """Map '/system/...' and remote paths to local badge tree."""
    s = str(p)
    if s.startswith("/system"):
        tail = s[len("/system"):].lstrip("/\\")
        return str(BADGE_ROOT / tail) if tail else str(BADGE_ROOT)
    if s.startswith(":/system"):
        tail = s[len(":/system"):].lstrip("/\\")
        return str(BADGE_ROOT / tail) if tail else str(BADGE_ROOT)
    if s.startswith("/state"):
        tail = s[len("/state"):].lstrip("/\\")
        return str(STATE_DIR / tail) if tail else str(STATE_DIR)
    return s


# Intercept os.chdir, os.listdir, and open
_real_chdir = os.chdir
_real_listdir = os.listdir
_real_open = builtins.open


def _safe_chdir(path: str | Path) -> None:
    _real_chdir(map_system_path(path))


def _safe_listdir(path: Any = ".") -> list[str]:
    if isinstance(path, (list, tuple)):
        path = path[0] if path else "."
    return _real_listdir(map_system_path(path))


def _safe_open(file: Any, *args, **kwargs):
    if isinstance(file, (str, Path)):
        file = map_system_path(file)
    return _real_open(file, *args, **kwargs)


class PathList(list):
    def __fspath__(self) -> str:
        return self[0] if self else ""

    def __add__(self, other: Any) -> Any:
        if isinstance(other, str):
            return (self[0] if self else "") + other
        return super().__add__(other)

    def __radd__(self, other: Any) -> Any:
        if isinstance(other, str):
            return other + (self[0] if self else "")
        return super().__radd__(other)


import importlib.machinery

orig_find_spec = importlib.machinery.PathFinder.find_spec


def hooked_find_spec(fullname: str, path: Any = None, target: Any = None):
    spec = orig_find_spec(fullname, path, target)
    if spec and spec.submodule_search_locations is not None:
        spec.submodule_search_locations = PathList(spec.submodule_search_locations)
    return spec


importlib.machinery.PathFinder.find_spec = staticmethod(hooked_find_spec)


class DictModule(ModuleType):
    def keys(self) -> Any:
        return getattr(self, "demos", self.__dict__).keys()

    def values(self) -> Any:
        return getattr(self, "demos", self.__dict__).values()

    def items(self) -> Any:
        return getattr(self, "demos", self.__dict__).items()

    def __getitem__(self, k: Any) -> Any:
        d = getattr(self, "demos", self.__dict__)
        return d[k]

    def __iter__(self) -> Any:
        d = getattr(self, "demos", self.__dict__)
        return iter(d)

    def __len__(self) -> int:
        d = getattr(self, "demos", self.__dict__)
        return len(d)


_real_import = builtins.__import__


def _safe_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
    if "/" in name or "\\" in name:
        p = Path(map_system_path(name))
        if not p.suffix:
            p = p.with_suffix(".py")
        mod_key = p.stem
        spec = importlib.util.spec_from_file_location(mod_key, str(p))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            sys.modules[mod_key] = mod
            spec.loader.exec_module(mod)
            return mod

    try:
        mod = _real_import(name, globals, locals, fromlist, level)
    except ModuleNotFoundError:
        mod = None
        for entry in list(sys.path):
            mapped_entry = Path(map_system_path(entry))
            candidate = mapped_entry / f"{name}.py"
            if candidate.exists():
                spec = importlib.util.spec_from_file_location(name, str(candidate))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[name] = mod
                    spec.loader.exec_module(mod)
                    break
            candidate_pkg = mapped_entry / name / "__init__.py"
            if candidate_pkg.exists():
                spec = importlib.util.spec_from_file_location(name, str(candidate_pkg))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[name] = mod
                    spec.loader.exec_module(mod)
                    break
        if mod is None:
            raise

    if hasattr(mod, "demos") and isinstance(mod.demos, dict):
        mod.__class__ = DictModule
    return mod


os.chdir = _safe_chdir  # type: ignore
os.listdir = _safe_listdir  # type: ignore
builtins.open = _safe_open  # type: ignore
builtins.__import__ = _safe_import  # type: ignore

# -----------------------------------------------------------------------------
# Geometry: vec2, rect, mat3
# -----------------------------------------------------------------------------

class vec2:
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        if isinstance(x, (tuple, list)):
            self.x = float(x[0])
            self.y = float(x[1])
        elif isinstance(x, vec2):
            self.x = x.x
            self.y = x.y
        else:
            self.x = float(x)
            self.y = float(y)

    def __repr__(self) -> str:
        return f"vec2({self.x}, {self.y})"

    def __iter__(self):
        yield self.x
        yield self.y

    def __len__(self) -> int:
        return 2

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError("vec2 index out of range")

    def __add__(self, other: Any) -> vec2:
        if isinstance(other, (vec2, tuple, list)):
            return vec2(self.x + other[0], self.y + other[1])
        return vec2(self.x + other, self.y + other)

    def __sub__(self, other: Any) -> vec2:
        if isinstance(other, (vec2, tuple, list)):
            return vec2(self.x - other[0], self.y - other[1])
        return vec2(self.x - other, self.y - other)

    def __mul__(self, other: Any) -> vec2:
        if isinstance(other, (vec2, tuple, list)):
            return vec2(self.x * other[0], self.y * other[1])
        return vec2(self.x * other, self.y * other)

    def __truediv__(self, other: Any) -> vec2:
        if isinstance(other, (vec2, tuple, list)):
            return vec2(self.x / other[0], self.y / other[1])
        return vec2(self.x / other, self.y / other)


class rect:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float = 0.0, y: float = 0.0, w: float = 0.0, h: float = 0.0):
        if isinstance(x, (tuple, list)):
            self.x = float(x[0])
            self.y = float(x[1])
            self.w = float(x[2]) if len(x) > 2 else 0.0
            self.h = float(x[3]) if len(x) > 3 else 0.0
        elif isinstance(x, rect):
            self.x, self.y, self.w, self.h = x.x, x.y, x.w, x.h
        else:
            self.x = float(x)
            self.y = float(y)
            self.w = float(w)
            self.h = float(h)

    @property
    def width(self) -> float:
        return self.w

    @width.setter
    def width(self, val: float) -> None:
        self.w = float(val)

    @property
    def height(self) -> float:
        return self.h

    @height.setter
    def height(self, val: float) -> None:
        self.h = float(val)

    def __repr__(self) -> str:
        return f"rect({self.x}, {self.y}, {self.w}, {self.h})"

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.w
        yield self.h

    def __len__(self) -> int:
        return 4

    def __getitem__(self, index: int) -> float:
        return (self.x, self.y, self.w, self.h)[index]


class mat3:
    """3x3 Affine transformation matrix."""

    def __init__(self, m: list[float] | None = None):
        self.m = m[:] if m else [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

    def translate(self, tx: float, ty: float) -> mat3:
        t = [1.0, 0.0, float(tx), 0.0, 1.0, float(ty), 0.0, 0.0, 1.0]
        return self._multiply(t)

    def scale(self, sx: float, sy: float | None = None) -> mat3:
        if sy is None:
            sy = sx
        s = [float(sx), 0.0, 0.0, 0.0, float(sy), 0.0, 0.0, 0.0, 1.0]
        return self._multiply(s)

    def rotate(self, angle_rad: float) -> mat3:
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        r = [c, -s, 0.0, s, c, 0.0, 0.0, 0.0, 1.0]
        return self._multiply(r)

    def _multiply(self, b: list[float]) -> mat3:
        a = self.m
        res = [
            a[0] * b[0] + a[1] * b[3] + a[2] * b[6],
            a[0] * b[1] + a[1] * b[4] + a[2] * b[7],
            a[0] * b[2] + a[1] * b[5] + a[2] * b[8],
            a[3] * b[0] + a[4] * b[3] + a[5] * b[6],
            a[3] * b[1] + a[4] * b[4] + a[5] * b[7],
            a[3] * b[2] + a[4] * b[5] + a[5] * b[8],
            a[6] * b[0] + a[7] * b[3] + a[8] * b[6],
            a[6] * b[1] + a[7] * b[4] + a[8] * b[7],
            a[6] * b[2] + a[7] * b[5] + a[8] * b[8],
        ]
        self.m = res
        return self

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        px = self.m[0] * x + self.m[1] * y + self.m[2]
        py = self.m[3] * x + self.m[4] * y + self.m[5]
        return px, py


# -----------------------------------------------------------------------------
# Color & Brush
# -----------------------------------------------------------------------------

class ColorObj:
    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = max(0, min(255, int(r)))
        self.g = max(0, min(255, int(g)))
        self.b = max(0, min(255, int(b)))
        self.a = max(0, min(255, int(a)))

    def __repr__(self) -> str:
        return f"color.rgb({self.r}, {self.g}, {self.b}, {self.a})"

    def __iter__(self):
        yield self.r
        yield self.g
        yield self.b
        yield self.a

    def __getitem__(self, index: int) -> int:
        return (self.r, self.g, self.b, self.a)[index]

    def to_pygame(self) -> pygame.Color:
        return pygame.Color(self.r, self.g, self.b, self.a)


class _ColorNamespace:
    @staticmethod
    def rgb(r: int, g: int, b: int, a: int = 255) -> ColorObj:
        return ColorObj(r, g, b, a)

    black = ColorObj(0, 0, 0)
    white = ColorObj(255, 255, 255)
    grey = ColorObj(128, 128, 128)
    blue = ColorObj(0, 100, 255)
    red = ColorObj(255, 50, 50)
    orange = ColorObj(255, 140, 0)
    green = ColorObj(50, 205, 50)
    yellow = ColorObj(255, 220, 0)
    lime = ColorObj(50, 255, 50)
    navy = ColorObj(0, 0, 128)
    grape = ColorObj(128, 0, 128)


color = _ColorNamespace()


def normalize_color(c: Any) -> pygame.Color:
    if isinstance(c, ColorObj):
        return c.to_pygame()
    if isinstance(c, (tuple, list)):
        if len(c) == 3:
            return pygame.Color(int(c[0]), int(c[1]), int(c[2]), 255)
        if len(c) >= 4:
            return pygame.Color(int(c[0]), int(c[1]), int(c[2]), int(c[3]))
    if isinstance(c, pygame.Color):
        return c
    return pygame.Color(255, 255, 255, 255)


class _BrushNamespace:
    RADIAL = 1
    LINEAR = 2

    @staticmethod
    def gradient(type_: int, *args, **kwargs) -> Any:
        return ColorObj(255, 255, 255, 200)

    @staticmethod
    def pattern(*args, **kwargs) -> Any:
        return ColorObj(200, 200, 200, 255)


brush = _BrushNamespace()

# -----------------------------------------------------------------------------
# Shapes
# -----------------------------------------------------------------------------

class ShapeObj:
    def __init__(self, kind: str, **kwargs):
        self.kind = kind
        self.kwargs = kwargs
        self.transform: mat3 | None = None


class _ShapeNamespace:
    @staticmethod
    def rectangle(x: float, y: float, w: float, h: float, radius: float = 0) -> ShapeObj:
        return ShapeObj("rectangle", x=float(x), y=float(y), w=float(w), h=float(h), radius=float(radius))

    @staticmethod
    def rounded_rectangle(x: float, y: float, w: float, h: float, radius: float, *radii) -> ShapeObj:
        return ShapeObj("rounded_rectangle", x=float(x), y=float(y), w=float(w), h=float(h), radius=float(radius))

    @staticmethod
    def squircle(x: float, y: float, radius: float, power: float = 4) -> ShapeObj:
        return ShapeObj("rounded_rectangle", x=float(x - radius), y=float(y - radius), w=float(radius * 2), h=float(radius * 2), radius=float(radius * 0.4))

    @staticmethod
    def circle(x: float | vec2, y: float | None = None, r: float = 0) -> ShapeObj:
        if isinstance(x, (vec2, tuple, list)):
            cx, cy, radius = float(x[0]), float(x[1]), float(y or 0)
        else:
            cx, cy, radius = float(x), float(y or 0), float(r)
        return ShapeObj("circle", cx=cx, cy=cy, r=radius)

    @staticmethod
    def line(x1: float, y1: float, x2: float, y2: float, width: float = 1.0) -> ShapeObj:
        return ShapeObj("line", x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2), width=float(width))

    @staticmethod
    def pie(cx: float, cy: float, r: float, a1: float = 0, a2: float = 360) -> ShapeObj:
        return ShapeObj("circle", cx=float(cx), cy=float(cy), r=float(r))

    @staticmethod
    def star(*args, **kwargs) -> ShapeObj:
        return ShapeObj("circle", cx=0, cy=0, r=10)

    @staticmethod
    def custom(points: list) -> ShapeObj:
        return ShapeObj("custom", points=points)


shape = _ShapeNamespace()

# -----------------------------------------------------------------------------
# Image & SpriteSheet
# -----------------------------------------------------------------------------

class Image:
    OFF = 0
    X2 = 1
    X4 = 2

    def __init__(self, surface: pygame.Surface):
        self._surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self.transform: mat3 | None = None

    @staticmethod
    def load(path: str | Path) -> Image:
        resolved = map_system_path(path)
        if not os.path.isabs(resolved) and not os.path.exists(resolved):
            cand = BADGE_ROOT / resolved
            if cand.exists():
                resolved = str(cand)

        if not os.path.exists(resolved):
            # Fallback placeholder surface
            surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            surf.fill((60, 120, 220, 255))
            return Image(surf)

        surf = pygame.image.load(resolved).convert_alpha()
        return Image(surf)

    def spritesheet(self, columns: int, rows: int) -> SpriteSheet:
        cell_w = self.width // max(1, columns)
        cell_h = self.height // max(1, rows)
        return SpriteSheet(self, columns, rows, cell_w, cell_h)

    def blit(self, src: Image, pos: vec2 | tuple[float, float]) -> None:
        px, py = int(round(pos[0])), int(round(pos[1]))
        self._surface.blit(src._surface, (px, py))


class SpriteSheet:
    def __init__(self, parent: Image, cols: int, rows: int, cell_w: int, cell_h: int):
        self.parent = parent
        self.cols = cols
        self.rows = rows
        self.cell_w = cell_w
        self.cell_h = cell_h

    def sprite(self, col: int, row: int) -> Image:
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        rect_area = pygame.Rect(col * self.cell_w, row * self.cell_h, self.cell_w, self.cell_h)
        sub = self.parent._surface.subsurface(rect_area).copy()
        return Image(sub)


image = Image

# -----------------------------------------------------------------------------
# Font Engine
# -----------------------------------------------------------------------------

class FontWrapper:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self._font = pygame.font.Font(None, size)

    def measure_text(self, text: str) -> tuple[int, int]:
        return self._font.size(str(text))

    def render(self, text: str, col: pygame.Color) -> pygame.Surface:
        return self._font.render(str(text), True, col)


class _FontNamespace:
    def __init__(self):
        pygame.font.init()
        self.nope = FontWrapper("nope", 14)
        self.sins = FontWrapper("sins", 14)
        self.ark = FontWrapper("ark", 16)
        self.ziplock = FontWrapper("ziplock", 20)
        self.smart = FontWrapper("smart", 14)
        self.absolute = FontWrapper("absolute", 24)
        self.curse = FontWrapper("curse", 18)
        self.fear = FontWrapper("fear", 16)
        self.winds = FontWrapper("winds", 14)
        self.hungry = FontWrapper("hungry", 14)
        self.ignore = FontWrapper("ignore", 16)

    def __getattr__(self, item: str) -> FontWrapper:
        # Fallback for any requested font name
        fw = FontWrapper(item, 16)
        setattr(self, item, fw)
        return fw


font = _FontNamespace()

# -----------------------------------------------------------------------------
# Screen Drawing Surface
# -----------------------------------------------------------------------------

class Screen:
    OFF = 0
    X2 = 1
    X4 = 2

    def __init__(self, width: int = 160, height: int = 120):
        self.width = width
        self.height = height
        self._surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.pen: Any = color.white
        self.font: FontWrapper = font.nope
        self.antialias: int = self.OFF
        self.clip = rect(0, 0, width, height)

    def _resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.clip = rect(0, 0, width, height)

    def clear(self, col: Any = None) -> None:
        c = normalize_color(col or self.pen)
        self._surface.fill(c)

    def blur(self, radius: int = 1) -> None:
        try:
            factor = max(1, int(radius) + 1)
            small = pygame.transform.smoothscale(
                self._surface,
                (max(1, self.width // factor), max(1, self.height // factor)),
            )
            self._surface = pygame.transform.smoothscale(small, (self.width, self.height))
        except Exception:
            pass

    def put(self, x: float, y: float) -> None:
        c = normalize_color(self.pen)
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.width and 0 <= iy < self.height:
            self._surface.set_at((ix, iy), c)

    def rectangle(self, *args) -> None:
        c = normalize_color(self.pen)
        if len(args) == 1:
            r = args[0]
            if isinstance(r, (rect, tuple, list)):
                pygame.draw.rect(self._surface, c, pygame.Rect(int(r[0]), int(r[1]), int(r[2]), int(r[3])))
            elif isinstance(r, pygame.Rect):
                pygame.draw.rect(self._surface, c, r)
        elif len(args) >= 4:
            x, y, w, h = args[:4]
            pygame.draw.rect(self._surface, c, pygame.Rect(int(x), int(y), int(w), int(h)))

    def circle(self, *args) -> None:
        c = normalize_color(self.pen)
        if len(args) == 2 and isinstance(args[0], (vec2, tuple, list)):
            cx, cy = int(round(args[0][0])), int(round(args[0][1]))
            r = int(round(args[1]))
        elif len(args) >= 3:
            cx, cy, r = int(round(args[0])), int(round(args[1])), int(round(args[2]))
        else:
            return
        pygame.draw.circle(self._surface, c, (cx, cy), max(0, r))

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        c = normalize_color(self.pen)
        pygame.draw.line(
            self._surface,
            c,
            (int(round(x1)), int(round(y1))),
            (int(round(x2)), int(round(y2))),
        )

    def shape(self, sh: ShapeObj) -> None:
        c = normalize_color(self.pen)
        kw = sh.kwargs
        kind = sh.kind

        if kind in ("rectangle", "rounded_rectangle"):
            x, y, w, h = kw["x"], kw["y"], kw["w"], kw["h"]
            if sh.transform:
                x, y = sh.transform.transform_point(x, y)
                w *= sh.transform.m[0]
                h *= sh.transform.m[4]
            r = int(kw.get("radius", 0))
            rx, ry = int(round(min(x, x + w))), int(round(min(y, y + h)))
            rw, rh = max(1, int(round(abs(w)))), max(1, int(round(abs(h))))
            pygame.draw.rect(self._surface, c, pygame.Rect(rx, ry, rw, rh), border_radius=r)

        elif kind == "circle":
            cx, cy, r = kw["cx"], kw["cy"], kw["r"]
            if sh.transform:
                cx, cy = sh.transform.transform_point(cx, cy)
            pygame.draw.circle(self._surface, c, (int(round(cx)), int(round(cy))), max(0, int(round(r))))

        elif kind == "line":
            x1, y1, x2, y2 = kw["x1"], kw["y1"], kw["x2"], kw["y2"]
            lw = max(1, int(round(kw.get("width", 1.0))))
            if sh.transform:
                x1, y1 = sh.transform.transform_point(x1, y1)
                x2, y2 = sh.transform.transform_point(x2, y2)
            pygame.draw.line(self._surface, c, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), width=lw)

    def blit(self, src: Image, dest: Any, src_rect: Any = None) -> None:
        if not isinstance(src, Image):
            return

        surf = src._surface
        if isinstance(dest, (vec2, tuple, list)) and len(dest) == 2:
            self._surface.blit(surf, (int(round(dest[0])), int(round(dest[1]))))

        elif isinstance(dest, (rect, tuple, list)) and len(dest) >= 4:
            dx, dy, dw, dh = dest[0], dest[1], dest[2], dest[3]
            nw = max(1, int(round(abs(dw))))
            nh = max(1, int(round(abs(dh))))
            scaled = pygame.transform.scale(surf, (nw, nh))
            if dw < 0:
                scaled = pygame.transform.flip(scaled, True, False)
            if dh < 0:
                scaled = pygame.transform.flip(scaled, False, True)
            self._surface.blit(scaled, (int(round(dx)), int(round(dy))))

    def text(self, msg: Any, *args, **kwargs) -> None:
        c = normalize_color(self.pen)
        if not args:
            return

        if len(args) == 1 and isinstance(args[0], (vec2, tuple, list)):
            x, y = int(round(args[0][0])), int(round(args[0][1]))
        elif len(args) == 1 and isinstance(args[0], rect):
            x, y = int(round(args[0].x)), int(round(args[0].y))
        elif len(args) >= 2:
            x, y = int(round(args[0])), int(round(args[1]))
        else:
            return

        rendered = self.font.render(str(msg), c)
        self._surface.blit(rendered, (x, y))

    def measure_text(self, text: str) -> tuple[int, int]:
        return self.font.measure_text(str(text))


# -----------------------------------------------------------------------------
# Input Constants & Badge Runtime
# -----------------------------------------------------------------------------

_active_badge_runtime: Any = None


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

    def pressed(self, action: str | None = None) -> bool | set[str]:
        if action is None:
            return set(self._pressed_this_frame)
        return action in self._pressed_this_frame

    def held(self, action: str | None = None) -> bool | set[str]:
        if action is None:
            return set(self._current_keys)
        return action in self._current_keys

    def released(self, action: str | None = None) -> bool | set[str]:
        if action is None:
            return set(self._released_this_frame)
        return action in self._released_this_frame

    def touched(self, action: str | None = None) -> bool | set[str]:
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

    def caselights(self, *args) -> None:
        pass

    def poll(self) -> None:
        pass


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


# -----------------------------------------------------------------------------
# Mock Hardware Modules
# -----------------------------------------------------------------------------

def install_mock_modules() -> None:
    # badgeware
    m_badgeware = ModuleType("badgeware")
    m_badgeware.State = State
    sys.modules["badgeware"] = m_badgeware

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

    for attr in ["BUTTON_HOME", "BUTTON_UP", "BUTTON_DOWN", "BUTTON_LEFT", "BUTTON_RIGHT", "BUTTON_SELECT", "BUTTON_BACK", "BUTTON_MENU"]:
        setattr(Pin.board, attr, Pin())

    class RTC:
        def datetime(self):
            now = time.localtime()
            return (now.tm_year, now.tm_mon, now.tm_mday, now.tm_wday, now.tm_hour, now.tm_min, now.tm_sec, 0)

    m_machine.Pin = Pin
    m_machine.RTC = RTC
    sys.modules["machine"] = m_machine

    # brand
    m_brand = ModuleType("brand")
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
    m_brand.BLACK = ColorObj(0, 0, 0)
    m_brand.WHITE = ColorObj(255, 255, 255)
    sys.modules["brand"] = m_brand

    # gc
    import gc
    gc.mem_free = lambda: 512000  # type: ignore

    # wifi & ntptime & utime
    sys.modules["utime"] = time

    m_wifi = ModuleType("wifi")
    m_wifi.is_connected = lambda: True
    m_wifi.connect = lambda *args, **kwargs: True
    m_wifi.disconnect = lambda: True
    sys.modules["wifi"] = m_wifi

    m_ntp = ModuleType("ntptime")
    m_ntp.settime = lambda: None
    sys.modules["ntptime"] = m_ntp

    # requests
    m_req = ModuleType("requests")
    class DummyResponse:
        def __init__(self):
            self.status_code = 200
            self.text = "{}"
        def json(self):
            return {}
        def close(self):
            pass
    m_req.get = lambda *args, **kwargs: DummyResponse()
    m_req.post = lambda *args, **kwargs: DummyResponse()
    sys.modules["requests"] = m_req

    # secrets
    m_sec = ModuleType("secrets")
    sec_path = BADGE_ROOT / "secrets.py"
    if sec_path.exists():
        try:
            exec(sec_path.read_text(encoding="utf-8"), m_sec.__dict__)
        except Exception:
            pass
    m_sec.require = lambda *args: True
    sys.modules["secrets"] = m_sec

    # powman
    m_powman = ModuleType("powman")
    m_powman.WAKE_POWER = 1
    m_powman.WAKE_WATCHDOG = 2
    m_powman.WAKE_DOUBLETAP = 3
    m_powman.get_wake_reason = lambda: m_powman.WAKE_POWER
    sys.modules["powman"] = m_powman

    # aye_arr.nec
    m_ayearr = ModuleType("aye_arr")
    m_nec = ModuleType("aye_arr.nec")

    class NECReceiver:
        def __init__(self, *args, **kwargs):
            pass

        def read(self):
            return None

    m_nec.NECReceiver = NECReceiver
    m_ayearr.nec = m_nec
    sys.modules["aye_arr"] = m_ayearr
    sys.modules["aye_arr.nec"] = m_nec


# -----------------------------------------------------------------------------
# Runner & App Lifecycle
# -----------------------------------------------------------------------------

class RunResult:
    def __init__(self, result: Any = None):
        self.result = result


class SimulatorApp:
    def __init__(self, scale: int = 4, screenshots_dir: Path | None = None, perf: bool = False, max_frames: int | None = None):
        self.scale = scale
        self.screenshots_dir = screenshots_dir or (REPO_ROOT / "screenshots")
        self.perf = perf
        self.max_frames = max_frames
        self.frame_count = 0

        pygame.init()
        pygame.display.set_caption("GitHub Universe 2026 Badge Simulator")

        self.screen_obj = Screen(160, 120)
        self.badge_obj = BadgeRuntime(self.screen_obj)

        self.window_surf: pygame.Surface | None = None
        self._update_window_size()

        self.clock = pygame.time.Clock()
        self.running = True
        self.next_app_to_launch: str | None = None

        # Expose globals into builtins
        self._inject_globals()

    def _update_window_size(self) -> None:
        target_w = self.screen_obj.width * self.scale
        target_h = self.screen_obj.height * self.scale
        self.window_surf = pygame.display.set_mode((target_w, target_h))

    def _inject_globals(self) -> None:
        import builtins

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

        builtins.run = self.run  # type: ignore
        builtins.launch = self.launch  # type: ignore
        builtins.reset = self.reset  # type: ignore
        builtins.file_exists = lambda p: os.path.exists(map_system_path(p))  # type: ignore
        builtins.is_dir = lambda p: os.path.isdir(map_system_path(p))  # type: ignore

    def save_screenshot(self) -> None:
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = self.screenshots_dir / f"screenshot_{timestamp}.png"
        pygame.image.save(self.screen_obj._surface, str(filename))
        print(f"[Screenshot] Saved native {self.screen_obj.width}x{self.screen_obj.height} to {filename}")

    def run(self, update_fn: Callable[[], Any]) -> RunResult:
        """Main loop executed by apps."""
        result: Any = None
        last_ticks = pygame.time.get_ticks()

        while self.running:
            # 1. Input processing
            self.badge_obj._pressed_this_frame.clear()
            self.badge_obj._released_this_frame.clear()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return RunResult(None)

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
                        self.next_app_to_launch = "/system/apps/menu"
                        return RunResult("/system/apps/menu")

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
            self.badge_obj.ticks_delta = max(1, now - last_ticks)
            last_ticks = now

            # 3. Call app frame
            try:
                ret = update_fn()
                if ret is not None:
                    result = ret
                    self.next_app_to_launch = str(ret)
                    break
            except Exception as e:
                import traceback
                print(f"[Simulator] Error in update(): {e}")
                traceback.print_exc()
                break

            # 4. Blit to window
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
                print(f"[Perf] FPS: {fps:.1f} | Resolution: {self.screen_obj.width}x{self.screen_obj.height} | Frame: {self.badge_obj.ticks_delta}ms")

            if self.max_frames is not None:
                self.frame_count += 1
                if self.frame_count >= self.max_frames:
                    self.running = False
                    break

        return RunResult(result)

    def launch(self, app_path: str) -> Any:
        mapped = map_system_path(app_path)
        p = Path(mapped)
        if not p.is_absolute():
            if (REPO_ROOT / p).exists():
                p = REPO_ROOT / p
            elif (APPS_DIR / p).exists():
                p = APPS_DIR / p
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
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
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
            except Exception as e:
                import traceback
                print(f"[Simulator] Crash in {app_name}: {e}")
                traceback.print_exc()

        return None

    def reset(self) -> None:
        print("[Simulator] Soft reset requested. Returning to menu...")
        self.launch("/system/apps/menu")


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub Universe 2026 Badge Simulator")
    parser.add_argument("app", nargs="?", default="menu", help="App name under badge/apps/ (default: menu)")
    parser.add_argument("--scale", type=int, default=4, help="Display scale factor (default: 4)")
    parser.add_argument("--screenshots", help="Directory to save screenshots when pressing F12")
    parser.add_argument("--perf", action="store_true", help="Print live performance statistics")
    parser.add_argument("--clean", action="store_true", help="Remove saved state before running")
    parser.add_argument("--frames", type=int, default=None, help="Exit after N frames (useful for headless testing)")

    args = parser.parse_args()

    if args.clean and STATE_DIR.exists():
        import shutil
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
    )

    sim.launch(app_path)
    while sim.running and sim.next_app_to_launch:
        next_app = sim.next_app_to_launch
        sim.next_app_to_launch = None
        sim.launch(next_app)

    return 0


if __name__ == "__main__":
    sys.exit(main())

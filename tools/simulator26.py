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
import types
from types import ModuleType, SimpleNamespace
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
BADGE_ROOT = REPO_ROOT / "badge"
APPS_DIR = BADGE_ROOT / "apps"
STATE_DIR = REPO_ROOT / ".badge_state"

try:
    import pygame
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


# Intercept os.chdir, os.listdir, os.rename, os.remove, and open
_real_chdir = os.chdir
_real_listdir = os.listdir
_real_rename = os.rename
_real_remove = os.remove
_real_open = builtins.open


def _safe_rename(src: Any, dst: Any) -> None:
    s = map_system_path(src)
    d = map_system_path(dst)
    parent = Path(d).parent
    parent.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "replace"):
        os.replace(s, d)
    else:
        try:
            os.remove(d)
        except OSError:
            pass
        _real_rename(s, d)


def _safe_remove(path: Any) -> None:
    resolved = map_system_path(path)
    if os.path.exists(resolved):
        _real_remove(resolved)


def _safe_chdir(path: str | Path) -> None:
    _real_chdir(map_system_path(path))


def _safe_listdir(path: Any = ".") -> list[str]:
    if isinstance(path, (list, tuple)):
        path = path[0] if path else "."
    return _real_listdir(map_system_path(path))


def _safe_ilistdir(path: Any = "."):
    resolved = Path(map_system_path(path))
    if not resolved.exists():
        return []
    result = []
    for entry in resolved.iterdir():
        type_flag = 0x4000 if entry.is_dir() else 0x8000
        result.append((entry.name, type_flag, 0))
    return result


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
            candidate_src = mapped_entry / "src" / f"{name}.py"
            target_file = candidate if candidate.exists() else (candidate_src if candidate_src.exists() else None)
            if target_file:
                spec = importlib.util.spec_from_file_location(name, str(target_file))
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
os.ilistdir = _safe_ilistdir  # type: ignore
os.rename = _safe_rename  # type: ignore
os.remove = _safe_remove  # type: ignore
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


class ImageBrush:
    def __init__(self, src: Any, transform: mat3 | None = None, filter_mode: Any = None):
        self.src = src
        self.transform = transform
        self.filter_mode = filter_mode

    def geometry(self, *args, **kwargs) -> Any:
        return self


class _BrushNamespace:
    RADIAL = 1
    LINEAR = 2

    @staticmethod
    def gradient(type_: int, *args, **kwargs) -> Any:
        return ColorObj(255, 255, 255, 200)

    @staticmethod
    def pattern(*args, **kwargs) -> Any:
        return ColorObj(200, 200, 200, 255)

    @staticmethod
    def image(src: Any, transform: mat3 | None = None, filter_mode: Any = None) -> ImageBrush:
        return ImageBrush(src, transform, filter_mode)

    @staticmethod
    def blur(radius: float = 1.0) -> Any:
        return ColorObj(200, 200, 200, 200)

    @staticmethod
    def erase(tint: Any = None) -> Any:
        return ColorObj(0, 0, 0, 0)

    @staticmethod
    def lighten(amount: float = 1.0) -> Any:
        return ColorObj(255, 255, 255, 100)

    @staticmethod
    def darken(amount: float = 1.0) -> Any:
        return ColorObj(0, 0, 0, 100)

    @staticmethod
    def duotone(c1: Any, c2: Any) -> Any:
        return ColorObj(150, 255, 170, 255)

    @staticmethod
    def pixelate(size: float = 1.0) -> Any:
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
        self.stroke_width: float | None = None

    def stroke(self, width: float = 1.0, *args, **kwargs):
        self.stroke_width = float(width)
        return self


class _ShapeNamespace:
    JOIN_MITER = 0
    JOIN_ROUND = 1
    JOIN_BEVEL = 2
    CAP_BUTT = 0
    CAP_ROUND = 1
    CAP_SQUARE = 2
    ALIGN_CENTER = 0
    ALIGN_INNER = 1
    ALIGN_OUTER = 2
    PATH_OPEN = 4

    @staticmethod
    def regular_polygon(x: float, y: float, radius: float, sides: int = 4, rotation: float = 0.0) -> ShapeObj:
        import math
        pts = []
        angle_step = 2.0 * math.pi / max(3, int(sides))
        for i in range(int(sides)):
            angle = i * angle_step + rotation
            pts.append(vec2(float(x) + float(radius) * math.cos(angle), float(y) + float(radius) * math.sin(angle)))
        return ShapeObj("custom", points=pts)
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
    def custom(*contours) -> ShapeObj:
        return ShapeObj("custom", contours=contours)


shape = _ShapeNamespace()

# -----------------------------------------------------------------------------
# Image & SpriteSheet
# -----------------------------------------------------------------------------

class Image:
    OFF = 0
    X2 = 1
    X4 = 2
    BILINEAR = 1
    NEAREST = 0
    NON_ZERO = 1
    EVEN_ODD = 0
    CENTER = 1
    LEFT = 2
    RIGHT = 3
    TOP = 4
    BOTTOM = 5
    RGB565 = 1
    QR_LOW = 1
    QR_MEDIUM = 2
    QR_HIGH = 3

    def __init__(self, surface: pygame.Surface):
        self._surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self.transform: mat3 | None = None

    @staticmethod
    def qr(url: str, ecc: int = 1, scale: int = 2) -> Image:
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        pygame.draw.rect(surf, (0, 0, 0, 255), pygame.Rect(4, 4, 16, 16), width=2)
        pygame.draw.rect(surf, (0, 0, 0, 255), pygame.Rect(44, 4, 16, 16), width=2)
        pygame.draw.rect(surf, (0, 0, 0, 255), pygame.Rect(4, 44, 16, 16), width=2)
        return Image(surf)

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

        try:
            surf = pygame.image.load(resolved).convert_alpha()
        except Exception:
            surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            surf.fill((88, 58, 247, 255))
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
        if isinstance(self.pen, ImageBrush) and getattr(self.pen, "src", None):
            src_surf = getattr(self.pen.src, "_surface", None)
            if src_surf:
                trans = sh.transform or self.pen.transform
                kw = sh.kwargs
                w = kw.get("w", src_surf.get_width())
                h = kw.get("h", src_surf.get_height())
                if trans:
                    xc, yc = trans.transform_point(w / 2.0, h / 2.0)
                    sx = math.hypot(trans.m[0], trans.m[3])
                    sy = math.hypot(trans.m[1], trans.m[4])
                    theta = math.atan2(trans.m[3], trans.m[0])
                    nw = max(1, int(round(src_surf.get_width() * sx)))
                    nh = max(1, int(round(src_surf.get_height() * sy)))
                    scaled = pygame.transform.scale(src_surf, (nw, nh))
                    deg = math.degrees(theta)
                    rotated = pygame.transform.rotate(scaled, -deg)
                    dst_rect = rotated.get_rect(center=(int(round(xc)), int(round(yc))))
                    self._surface.blit(rotated, dst_rect)
                    return
                else:
                    x = kw.get("x", 0)
                    y = kw.get("y", 0)
                    self._surface.blit(src_surf, (int(round(x)), int(round(y))))
                    return

        c = normalize_color(self.pen)
        kw = sh.kwargs
        kind = sh.kind

        sw = int(round(sh.stroke_width)) if sh.stroke_width is not None else 0
        if kind in ("rectangle", "rounded_rectangle"):
            x, y, w, h = kw["x"], kw["y"], kw["w"], kw["h"]
            if sh.transform:
                x, y = sh.transform.transform_point(x, y)
                w *= sh.transform.m[0]
                h *= sh.transform.m[4]
            r = int(kw.get("radius", 0))
            rx, ry = int(round(min(x, x + w))), int(round(min(y, y + h)))
            rw, rh = max(1, int(round(abs(w)))), max(1, int(round(abs(h))))
            pygame.draw.rect(self._surface, c, pygame.Rect(rx, ry, rw, rh), width=sw, border_radius=r)

        elif kind == "circle":
            cx, cy, r = kw["cx"], kw["cy"], kw["r"]
            if sh.transform:
                cx, cy = sh.transform.transform_point(cx, cy)
            pygame.draw.circle(self._surface, c, (int(round(cx)), int(round(cy))), max(0, int(round(r))), width=sw)

        elif kind == "line":
            x1, y1, x2, y2 = kw["x1"], kw["y1"], kw["x2"], kw["y2"]
            lw = max(1, int(round(kw.get("width", 1.0))))
            if sh.transform:
                x1, y1 = sh.transform.transform_point(x1, y1)
                x2, y2 = sh.transform.transform_point(x2, y2)
            pygame.draw.line(self._surface, c, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), width=lw)

        elif kind == "custom":
            contours = kw.get("contours") or ([kw["points"]] if "points" in kw else [])
            for poly in contours:
                pts = []
                if len(poly) > 0:
                    if isinstance(poly[0], (int, float)):
                        pts = [(int(round(poly[i])), int(round(poly[i + 1]))) for i in range(0, len(poly) - 1, 2)]
                    else:
                        pts = [(int(round(p[0])), int(round(p[1]))) for p in poly]
                if len(pts) >= 3:
                    pygame.draw.polygon(self._surface, c, pts, width=sw)
                elif len(pts) == 2:
                    pygame.draw.line(self._surface, c, pts[0], pts[1], width=max(1, sw))

    def blit(self, src: Image, *args, **kwargs) -> None:
        if not isinstance(src, Image):
            return

        surf = src._surface
        if not args:
            return

        # 1. Positional x, y: screen.blit(img, x, y)
        if len(args) >= 2 and isinstance(args[0], (int, float)) and isinstance(args[1], (int, float)):
            self._surface.blit(surf, (int(round(args[0])), int(round(args[1]))))
            return

        # 2. Source rect + Destination rect: screen.blit(img, src_rect, dest_rect, [filter])
        if len(args) >= 2 and hasattr(args[0], "__len__") and len(args[0]) >= 4 and hasattr(args[1], "__len__") and len(args[1]) >= 4:
            src_rect = args[0]
            dest_rect = args[1]
            sx, sy, sw, sh = int(round(src_rect[0])), int(round(src_rect[1])), int(round(src_rect[2])), int(round(src_rect[3]))
            sub_rect = pygame.Rect(sx, sy, max(1, sw), max(1, sh)).clip(surf.get_rect())
            cropped = surf.subsurface(sub_rect) if sub_rect.width > 0 and sub_rect.height > 0 else surf
            dx, dy, dw, dh = dest_rect[0], dest_rect[1], dest_rect[2], dest_rect[3]
            nw = max(1, int(round(abs(dw))))
            nh = max(1, int(round(abs(dh))))
            scaled = pygame.transform.scale(cropped, (nw, nh))
            if dw < 0:
                scaled = pygame.transform.flip(scaled, True, False)
            if dh < 0:
                scaled = pygame.transform.flip(scaled, False, True)
            self._surface.blit(scaled, (int(round(dx)), int(round(dy))))
            return

        # 3. Destination vec2 or rect: screen.blit(img, dest, [filter])
        dest = args[0]
        if isinstance(dest, (vec2, tuple, list)) and len(dest) == 2:
            self._surface.blit(surf, (int(round(dest[0])), int(round(dest[1]))))
        elif hasattr(dest, "__len__") and len(dest) >= 4:
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

        size = kwargs.get("font_size") or (int(round(args[2])) if len(args) >= 3 and isinstance(args[2], (int, float)) else None)
        if size:
            f = pygame.font.Font(None, int(round(size)))
            rendered = f.render(str(msg), True, c)
        else:
            rendered = self.font.render(str(msg), c)
        self._surface.blit(rendered, (x, y))

    def measure_text(self, text: str, font_size: int | None = None, *args, **kwargs) -> tuple[int, int]:
        if font_size:
            f = pygame.font.Font(None, int(round(font_size)))
            return f.size(str(text))
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


class ButtonGroup:
    def __init__(self, runtime: "BadgeRuntime", allowed: set[str] | None = None):
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

class DisplayMock:
    def set_async(self, async_mode: bool = True) -> None:
        pass

    def update(self) -> None:
        pass

    def backlight(self, level: float = 1.0) -> None:
        pass

    def brightness(self, level: float = 1.0) -> None:
        pass


def install_mock_modules() -> None:
    # display
    m_display = ModuleType("display")
    m_display.set_async = lambda *args, **kwargs: None
    m_display.update = lambda *args, **kwargs: None
    m_display.backlight = lambda *args, **kwargs: None
    m_display.brightness = lambda *args, **kwargs: None
    sys.modules["display"] = m_display

    # easing
    import math
    m_easing = ModuleType("easing")
    m_easing.easeOutCubic = lambda t: 1.0 - (1.0 - max(0.0, min(1.0, float(t)))) ** 3
    m_easing.easeInOutCubic = lambda t: 4.0 * t ** 3 if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
    c1 = 1.70158
    c3 = c1 + 1.0
    m_easing.easeOutBack = lambda t: 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)
    m_easing.easeOutElastic = lambda t: 0.0 if t <= 0 else (1.0 if t >= 1 else 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * (2.0 * math.pi) / 3.0) + 1.0)
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
        def leave(self):
            pass
        def pump(self):
            pass
        def update(self):
            pass
        def receive(self):
            return []
        def send(self, data):
            pass

    class MockProximity:
        def __init__(self, link):
            pass
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
        def draw_identicon(self, scr, badge_id, x, y, size):
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
                            rect_cell = pygame.Rect(int(x + c * cell), int(y + row * cell), int(cell) + 1, int(cell) + 1)
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
            try:
                import urllib.request
                req = urllib.request.Request(self.url, headers=self.headers or {"User-Agent": "GitHub Universe Badge 2026"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        resolved_dest.write_bytes(resp.read())
                        fetched = True
            except Exception:
                fetched = False
            if not fetched and not resolved_dest.exists():
                if "badge_user.json" in str(dest):
                    handle_name = getattr(m_sec, "GITHUB_USERNAME", "mgliot") or "mgliot"
                    contact_name = getattr(m_sec, "CONTACT_NAME", "Marcelino Gonzalez") or "Marcelino Gonzalez"
                    resolved_dest.write_text(json.dumps({
                        "login": handle_name,
                        "name": contact_name,
                        "followers": 18,
                        "public_repos": 12
                    }), encoding="utf-8")
                elif "badge_contribs.json" in str(dest):
                    weeks = []
                    for w in range(52):
                        days = [{"level": (w + d) % 4} for d in range(7)]
                        weeks.append({"contribution_days": days})
                    resolved_dest.write_text(json.dumps({
                        "total_contributions": 342,
                        "weeks": weeks
                    }), encoding="utf-8")
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
        screen.pen = color.rgb(255, 255, 255)
        for i, line in enumerate(message_tuple):
            screen.text(line, 20, 40 + i * 20)
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

    for attr in ["BUTTON_HOME", "BUTTON_UP", "BUTTON_DOWN", "BUTTON_LEFT", "BUTTON_RIGHT", "BUTTON_SELECT", "BUTTON_BACK", "BUTTON_MENU"]:
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
    m_wifi.failure = lambda: False
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

    # powman
    m_powman = ModuleType("powman")
    m_powman.WAKE_POWER = 1
    m_powman.WAKE_WATCHDOG = 2
    m_powman.WAKE_DOUBLETAP = 3
    m_powman.get_wake_reason = lambda: m_powman.WAKE_POWER
    sys.modules["powman"] = m_powman

    # aye_arr.nec & remotes
    m_ayearr = ModuleType("aye_arr")
    m_ayearr.__path__ = []
    m_nec = ModuleType("aye_arr.nec")
    m_nec.__path__ = []

    class NECReceiver:
        def __init__(self, *args, **kwargs):
            pass

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


# -----------------------------------------------------------------------------
# Runner & App Lifecycle
# -----------------------------------------------------------------------------

class RunResult:
    def __init__(self, result: Any = None):
        self.result = result


class SimulatorApp:
    def __init__(self, scale: int = 4, screenshots_dir: Path | None = None, perf: bool = False, max_frames: int | None = None, save_screenshot: Path | None = None):
        self.scale = scale
        self.screenshots_dir = screenshots_dir or (REPO_ROOT / "screenshots")
        self.perf = perf
        self.max_frames = max_frames
        self.frame_count = 0
        self.save_screenshot = save_screenshot

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

        builtins.display = DisplayMock()  # type: ignore

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

        if self.save_screenshot:
            self.save_screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.screen_obj._surface, str(self.save_screenshot))
            print(f"[Screenshot] Saved frame to {self.save_screenshot}")

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
    parser.add_argument("--save-screenshot", help="Save final frame image to this path on exit")

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

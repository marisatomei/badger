"""Geometry (vec2, rect, mat3), colors, brushes, and shape primitives."""

from __future__ import annotations

import math
from typing import Any

import pygame

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

    def translate(self, tx: float | vec2 | tuple | list, ty: float = 0.0) -> mat3:
        if isinstance(tx, (vec2, tuple, list)):
            tx, ty = float(tx[0]), float(tx[1])
        t = [1.0, 0.0, float(tx), 0.0, 1.0, float(ty), 0.0, 0.0, 1.0]
        return self._multiply(t)

    def scale(self, sx: float, sy: float | None = None) -> mat3:
        if sy is None:
            sy = sx
        s = [float(sx), 0.0, 0.0, 0.0, float(sy), 0.0, 0.0, 0.0, 1.0]
        return self._multiply(s)

    def rotate(self, angle_deg: float) -> mat3:
        rad = math.radians(angle_deg)
        c = math.cos(rad)
        s = math.sin(rad)
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

    def darken(self, amount: int | float = 20) -> ColorObj:
        if isinstance(amount, float) and 0.0 <= amount <= 1.0:
            factor = 1.0 - amount
            return ColorObj(round(self.r * factor), round(self.g * factor), round(self.b * factor), self.a)
        amt = int(round(amount))
        return ColorObj(self.r - amt, self.g - amt, self.b - amt, self.a)

    def lighten(self, amount: int | float = 20) -> ColorObj:
        if isinstance(amount, float) and 0.0 <= amount <= 1.0:
            return ColorObj(
                round(self.r + (255 - self.r) * amount),
                round(self.g + (255 - self.g) * amount),
                round(self.b + (255 - self.b) * amount),
                self.a,
            )
        amt = int(round(amount))
        return ColorObj(self.r + amt, self.g + amt, self.b + amt, self.a)


class _ColorNamespace:
    @staticmethod
    def rgb(r: int, g: int, b: int, a: int = 255) -> ColorObj:
        return ColorObj(r, g, b, a)

    @staticmethod
    def hsv(h: float, s: float, v: float, a: int = 255) -> ColorObj:
        import colorsys

        r, g, b = colorsys.hsv_to_rgb(float(h) % 1.0, max(0.0, min(1.0, float(s))), max(0.0, min(1.0, float(v))))
        return ColorObj(round(r * 255), round(g * 255), round(b * 255), a)

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
        return ShapeObj(
            "rounded_rectangle",
            x=float(x - radius),
            y=float(y - radius),
            w=float(radius * 2),
            h=float(radius * 2),
            radius=float(radius * 0.4),
        )

    @staticmethod
    def circle(x: float | vec2, y: float | None = None, r: float = 0) -> ShapeObj:
        if isinstance(x, (vec2, tuple, list)):
            cx, cy, radius = float(x[0]), float(x[1]), float(y or 0)
        else:
            cx, cy, radius = float(x), float(y or 0), float(r)
        return ShapeObj("circle", cx=cx, cy=cy, r=radius)

    @staticmethod
    def line(*args, **kwargs) -> ShapeObj:
        width = float(kwargs.get("width", 1.0))
        if len(args) == 2 or (len(args) == 3 and not isinstance(args[2], (int, float))):
            p1, p2 = args[0], args[1]
            return ShapeObj("line", x1=float(p1[0]), y1=float(p1[1]), x2=float(p2[0]), y2=float(p2[1]), width=width)
        elif len(args) >= 4:
            x1, y1, x2, y2 = args[0], args[1], args[2], args[3]
            w = float(args[4]) if len(args) >= 5 else width
            return ShapeObj("line", x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2), width=w)
        elif len(args) == 3 and isinstance(args[2], (int, float)):
            p1, p2, w = args[0], args[1], float(args[2])
            return ShapeObj("line", x1=float(p1[0]), y1=float(p1[1]), x2=float(p2[0]), y2=float(p2[1]), width=w)
        return ShapeObj("line", x1=0.0, y1=0.0, x2=0.0, y2=0.0, width=width)

    @staticmethod
    def arc(cx: float, cy: float, r1: float, r2: float, a1: float = 0, a2: float = 360) -> ShapeObj:
        return ShapeObj("circle", cx=float(cx), cy=float(cy), r=float(r2))

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

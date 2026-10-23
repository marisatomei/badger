"""Image, SpriteSheet, FontEngine, and Screen drawing surface."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pygame

from sim26.primitives import (
    ImageBrush,
    ShapeObj,
    color,
    mat3,
    normalize_color,
    rect,
    vec2,
)
from sim26.vfs import BADGE_ROOT, map_system_path

# -----------------------------------------------------------------------------
# Font Engine
# -----------------------------------------------------------------------------


_ICON_GLYPHS: dict[tuple[str, str], tuple[str, ...]] = {
    # Food icons (12x12 interior, rendered into 14x16 with 1px outline)
    ("food", "*"): (  # Candy
        "............",
        ".##......##.",
        ".###.##.###.",
        "..########..",
        "...##@@##...",
        "..###@#@@#..",
        "..###@@###..",
        "...######...",
        "..########..",
        ".###.##.###.",
        ".##......##.",
        "............",
    ),
    ("food", "7"): (  # Fruit
        ".....@@.....",
        "....@###....",
        ".....@......",
        "..########..",
        ".##########.",
        ".##@#@@####.",
        ".##@#######.",
        ".##########.",
        ".##########.",
        "..########..",
        "...######...",
        "............",
    ),
    ("food", "9"): (  # Burger
        "...######...",
        "..########..",
        ".##@#@@#@##.",
        ".##########.",
        ".@@@@@@@@@@.",
        "############",
        ".@@@@@@@@@@.",
        ".##########.",
        ".##########.",
        "..########..",
        "............",
        "............",
    ),
    ("food", ">"): (  # Pizza / wedge
        ".##.........",
        ".####.......",
        ".#@####.....",
        ".#@######...",
        ".#@###@@###.",
        ".#@########.",
        ".#@##@@###..",
        ".#@#####....",
        ".#@###......",
        ".###........",
        "............",
        "............",
    ),
    ("food", "2"): (  # Cupcake
        ".....##.....",
        "...######...",
        "..########..",
        ".###@##@###.",
        ".##########.",
        ".@@@@@@@@@@.",
        "..########..",
        "..#@#@@#@#..",
        "..#@#@@#@#..",
        "...######...",
        "............",
        "............",
    ),
    ("food", "I"): (  # Drink cup with straw
        "......##....",
        ".....##.....",
        ".....##.....",
        "..########..",
        ".@@@@@@@@@@.",
        "..########..",
        "..########..",
        "..@@@@@@@@..",
        "...######...",
        "...######...",
        "...######...",
        "............",
    ),
    # Hat icons
    ("hats", ","): (  # Crown
        "............",
        ".#...##...#.",
        ".##..##..##.",
        ".###.##.###.",
        ".##########.",
        ".##########.",
        ".##@#@@#@##.",
        ".##########.",
        ".@@@@@@@@@@.",
        ".##########.",
        "............",
        "............",
    ),
    ("hats", "O"): (  # Bowler hat
        "............",
        "...######...",
        "..########..",
        ".##########.",
        ".##########.",
        ".##########.",
        ".@@@@@@@@@@.",
        "############",
        "############",
        ".##########.",
        "............",
        "............",
    ),
    ("hats", ">"): (  # Cap
        "............",
        "....####....",
        "..########..",
        ".#####@####.",
        ".#####@####.",
        ".#####@####.",
        ".@@@@@@@@@@.",
        ".###########",
        "......######",
        "............",
        "............",
        "............",
    ),
    ("hats", "J"): (  # Top hat
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        "..########..",
        "..@@@@@@@@..",
        "..########..",
        "############",
        "############",
        "............",
        "............",
    ),
    ("hats", "M"): (  # Beanie / party hat
        "....####....",
        "....####....",
        "....@@@@....",
        "...######...",
        "..########..",
        "..@@@@@@@@..",
        ".##########.",
        ".##########.",
        "############",
        "###@####@###",
        "............",
        "............",
    ),
    ("hats", "+"): (  # Propeller hat
        "..###@@###..",
        ".....@@.....",
        "...######...",
        "..########..",
        ".##########.",
        ".##########.",
        ".@@@@@@@@@@.",
        "############",
        "............",
        "............",
        "............",
        "............",
    ),
    # Emoji icons
    ("emoji", ")"): (  # Sad face
        "............",
        "...######...",
        "..########..",
        ".##########.",
        ".###@##@###.",
        ".###@##@###.",
        ".##########.",
        ".###@@@@###.",
        ".##@####@##.",
        "..########..",
        "...######...",
        "............",
    ),
}


_FONT_CACHE: dict[int, pygame.font.Font] = {}


def _load_sys_font(size: int) -> pygame.font.Font:
    # Pygame's Font(None, n) uses a high-DPI point size where 16pt renders ~11px tall,
    # whereas SysFont uses pixel-closer point sizes where 16pt renders ~22px tall.
    # Scale by 0.68 so text layout matches hardware/Font(None) metrics while fixing "tt" kerning.
    pt = max(8, int(round(size * 0.68)))
    if pt not in _FONT_CACHE:
        try:
            _FONT_CACHE[pt] = pygame.font.SysFont("segoeui,arial,helvetica,dejavusans,sans-serif", pt)
        except Exception:
            _FONT_CACHE[pt] = pygame.font.Font(None, size)
    return _FONT_CACHE[pt]


class FontWrapper:
    def __init__(self, name: str, size: int):
        self.name = str(name)
        self.size = size
        self._font = _load_sys_font(size)

    @property
    def _base_family(self) -> str:
        return self.name[:-8] if self.name.endswith("_outline") else self.name

    @property
    def _is_outline(self) -> bool:
        return self.name.endswith("_outline")

    def measure_text(self, text: str) -> tuple[int, int]:
        if self._base_family in ("food", "hats", "emoji"):
            return (14 * max(1, len(str(text))), 16)
        return self._font.size(str(text))

    def render(self, text: str, col: pygame.Color) -> pygame.Surface:
        s = str(text)
        base = self._base_family
        if (base, s) in _ICON_GLYPHS:
            grid = _ICON_GLYPHS[(base, s)]
            surf = pygame.Surface((14, 16), pygame.SRCALPHA)
            filled = set()
            inner = set()
            for r, row in enumerate(grid):
                for c, ch in enumerate(row):
                    if ch == "#":
                        filled.add((c + 1, r + 2))
                    elif ch == "@":
                        inner.add((c + 1, r + 2))
            if not self._is_outline:
                for x, y in filled:
                    surf.set_at((x, y), col)
            else:
                solid = filled | inner
                outline_px = set(inner)
                for x, y in solid:
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < 14 and 0 <= ny < 16 and (nx, ny) not in solid:
                                outline_px.add((nx, ny))
                for x, y in outline_px:
                    surf.set_at((x, y), col)
            return surf

        rendered = self._font.render(s, True, col)
        if not self._is_outline:
            return rendered
        w, h = rendered.get_size()
        out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            out.blit(rendered, (dx + 1, dy + 1))
        return out


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

    def load(self, name: str, size: int = 16) -> FontWrapper:
        return getattr(self, str(name), FontWrapper(str(name), size))

    def __getattr__(self, item: str) -> FontWrapper:
        # Fallback for any requested font name
        fw = FontWrapper(item, 16)
        setattr(self, item, fw)
        return fw


font = _FontNamespace()

# -----------------------------------------------------------------------------
# Image, SpriteSheet & Screen Drawing Surface
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

    def __init__(self, width_or_surface: int | pygame.Surface = 160, height: int = 120, *args):
        if isinstance(width_or_surface, pygame.Surface):
            self._surface = width_or_surface
            self.width = width_or_surface.get_width()
            self.height = width_or_surface.get_height()
        else:
            self.width = max(1, int(width_or_surface))
            self.height = max(1, int(height))
            self._surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.transform: mat3 | None = None
        self.pen: Any = color.white
        self.font: FontWrapper = font.nope
        self.antialias: int = self.OFF
        self.alpha: int = 255
        self.fill_rule: int = self.NON_ZERO
        self.cursor: vec2 = vec2(0, 0)
        self._clip = rect(0, 0, self.width, self.height)

    @property
    def raw(self) -> Any:
        return memoryview(self._surface.get_view("0"))

    @property
    def clip(self) -> rect:
        return self._clip

    @clip.setter
    def clip(self, val: Any) -> None:
        if val is None:
            self._clip = rect(0, 0, self.width, self.height)
            self._surface.set_clip(None)
            return
        r = val if isinstance(val, rect) else rect(val)
        self._clip = r
        cx = int(round(r.x))
        cy = int(round(r.y))
        cw = max(0, int(round(r.w)))
        ch = max(0, int(round(r.h)))
        if cx <= 0 and cy <= 0 and cw >= self.width and ch >= self.height:
            self._surface.set_clip(None)
        else:
            self._surface.set_clip(pygame.Rect(cx, cy, cw, ch))

    def _resize(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.clip = rect(0, 0, width, height)

    @staticmethod
    def _resolve_path(path: str | Path) -> str:
        resolved = map_system_path(path)
        if not os.path.isabs(resolved) and not os.path.exists(resolved):
            cand = BADGE_ROOT / resolved
            if cand.exists():
                resolved = str(cand)
        return resolved

    @staticmethod
    def qr(url: str, ecc: int = 1, scale: int = 2) -> Image:
        n = 25
        pad = 2
        total = n + pad * 2
        px = max(1, int(scale))
        surf = pygame.Surface((total * px, total * px), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))

        grid = [[False] * n for _ in range(n)]
        reserved = [[False] * n for _ in range(n)]

        def place_finder(ox: int, oy: int) -> None:
            for r in range(-1, 8):
                for c in range(-1, 8):
                    rx, ry = ox + c, oy + r
                    if 0 <= rx < n and 0 <= ry < n:
                        reserved[ry][rx] = True
                        if 0 <= r <= 6 and 0 <= c <= 6:
                            grid[ry][rx] = (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))

        place_finder(0, 0)
        place_finder(n - 7, 0)
        place_finder(0, n - 7)

        # Alignment pattern at (16, 16) for version 2 (25x25)
        for r in range(16, 21):
            for c in range(16, 21):
                reserved[r][c] = True
                grid[r][c] = (r in (16, 20) or c in (16, 20) or (r == 18 and c == 18))

        # Timing patterns
        for i in range(8, n - 8):
            reserved[6][i] = reserved[i][6] = True
            grid[6][i] = grid[i][6] = (i % 2 == 0)

        # Deterministic data modules from URL
        payload = url.encode("utf-8") or b"https://badge"
        bit_idx = 0
        for r in range(n):
            for c in range(n):
                if not reserved[r][c]:
                    b_val = payload[(bit_idx // 8) % len(payload)]
                    shift = 7 - (bit_idx % 8)
                    mask = ((r * 31 + c * 17 + bit_idx) & 1)
                    grid[r][c] = bool(((b_val >> shift) & 1) ^ mask)
                    bit_idx += 1

        black = (0, 0, 0, 255)
        for r in range(n):
            for c in range(n):
                if grid[r][c]:
                    pygame.draw.rect(surf, black, pygame.Rect((c + pad) * px, (r + pad) * px, px, px))
        return Image(surf)

    @staticmethod
    def load(path: str | Path) -> Image:
        resolved = Image._resolve_path(path)
        if not os.path.exists(resolved):
            surf = pygame.Surface((24, 24), pygame.SRCALPHA)
            surf.fill((60, 120, 220, 255))
            return Image(surf)

        try:
            surf = pygame.image.load(resolved).convert_alpha()
        except Exception:
            surf = pygame.Surface((80, 80), pygame.SRCALPHA)
            surf.fill((88, 58, 247, 255))
        return Image(surf)

    def load_into(self, path: str | Path) -> None:
        resolved = Image._resolve_path(path)
        if not os.path.exists(resolved):
            raise OSError(f"File not found: {path}")
        try:
            surf = pygame.image.load(resolved).convert_alpha()
        except Exception as e:
            raise OSError(str(e)) from e
        self._surface.fill((0, 0, 0, 0))
        self._surface.blit(surf, (0, 0))

    def spritesheet(self, columns: int, rows: int) -> SpriteSheet:
        cell_w = self.width // max(1, columns)
        cell_h = self.height // max(1, rows)
        return SpriteSheet(self, columns, rows, cell_w, cell_h)

    def clear(self, col: Any = None) -> None:
        c = normalize_color(col or self.pen)
        self._surface.fill(c)

    def crt(self, spacing: int = 2, darkness: int = 28, *args) -> None:
        step = max(2, int(spacing))
        alpha = max(0, min(255, int(darkness)))
        if alpha <= 0:
            return
        line_surf = pygame.Surface((self.width, 1), pygame.SRCALPHA)
        line_surf.fill((0, 0, 0, alpha))
        for y in range(0, self.height, step):
            self._surface.blit(line_surf, (0, y))

    def dither(self, *args, **kwargs) -> None:
        pass

    def chromatic(self, *args, **kwargs) -> None:
        pass

    def glitch(self, *args, **kwargs) -> None:
        pass

    def bloom(self, *args, **kwargs) -> None:
        pass

    def window(self, *args) -> Image:
        if len(args) == 1 and hasattr(args[0], "__len__") and len(args[0]) >= 4:
            x, y, w, h = args[0][0], args[0][1], args[0][2], args[0][3]
        elif len(args) >= 4:
            x, y, w, h = args[0], args[1], args[2], args[3]
        else:
            return Image(self._surface)
        sub_rect = pygame.Rect(int(round(x)), int(round(y)), max(1, int(round(w))), max(1, int(round(h)))).clip(
            self._surface.get_rect()
        )
        if sub_rect.width <= 0 or sub_rect.height <= 0:
            return Image(1, 1)
        return Image(self._surface.subsurface(sub_rect))

    def triangle(self, *args) -> None:
        c = normalize_color(self.pen)
        if len(args) == 3:
            p1, p2, p3 = args[0], args[1], args[2]
            pts = [(int(round(p1[0])), int(round(p1[1]))), (int(round(p2[0])), int(round(p2[1]))), (int(round(p3[0])), int(round(p3[1])))]
        elif len(args) >= 6:
            pts = [(int(round(args[0])), int(round(args[1]))), (int(round(args[2])), int(round(args[3]))), (int(round(args[4])), int(round(args[5])))]
        else:
            return
        pygame.draw.polygon(self._surface, c, pts)

    def blit_vspan(self, src: Image, x: float, y: float, h: float, u: float, v1: float = 0.0, v2: float = 1.0) -> None:
        if not isinstance(src, Image) or h <= 0:
            return
        sx = max(0, min(src.width - 1, int(u * src.width) if u <= 1.0 else int(u)))
        sy1 = max(0, min(src.height - 1, int(v1 * src.height) if v1 <= 1.0 else int(v1)))
        sy2 = max(sy1 + 1, min(src.height, int(v2 * src.height) if v2 <= 1.0 else int(v2)))
        col_surf = src._surface.subsurface(pygame.Rect(sx, sy1, 1, max(1, sy2 - sy1)))
        scaled = pygame.transform.scale(col_surf, (1, max(1, int(round(h)))))
        self._surface.blit(scaled, (int(round(x)), int(round(y))))

    def draw(self, sh: ShapeObj) -> None:
        self.shape(sh)

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

    def line(self, *args) -> None:
        c = normalize_color(self.pen)
        w = 1
        if len(args) >= 2 and isinstance(args[0], (vec2, tuple, list)) and isinstance(args[1], (vec2, tuple, list)):
            x1, y1 = args[0][0], args[0][1]
            x2, y2 = args[1][0], args[1][1]
            if len(args) >= 3:
                w = max(1, int(round(args[2])))
        elif len(args) >= 4:
            x1, y1, x2, y2 = args[0], args[1], args[2], args[3]
            if len(args) >= 5:
                w = max(1, int(round(args[4])))
        else:
            return
        pygame.draw.line(
            self._surface,
            c,
            (int(round(x1)), int(round(y1))),
            (int(round(x2)), int(round(y2))),
            w,
        )

    def shapes(self, shape_list: Any) -> None:
        if shape_list:
            for sh in shape_list:
                self.shape(sh)

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
                r *= math.hypot(sh.transform.m[0], sh.transform.m[3])
            pygame.draw.circle(self._surface, c, (int(round(cx)), int(round(cy))), max(0, int(round(r))), width=sw)

        elif kind == "ellipse":
            cx, cy, rx, ry = kw["cx"], kw["cy"], kw["rx"], kw["ry"]
            if sh.transform:
                cx, cy = sh.transform.transform_point(cx, cy)
                rx *= math.hypot(sh.transform.m[0], sh.transform.m[3])
                ry *= math.hypot(sh.transform.m[1], sh.transform.m[4])
            ew = max(1, int(round(abs(rx) * 2)))
            eh = max(1, int(round(abs(ry) * 2)))
            erect = pygame.Rect(int(round(cx - ew / 2)), int(round(cy - eh / 2)), ew, eh)
            pygame.draw.ellipse(self._surface, c, erect, width=sw)

        elif kind == "line":
            x1, y1, x2, y2 = kw["x1"], kw["y1"], kw["x2"], kw["y2"]
            lw = max(1, int(round(kw.get("width", 1.0))))
            if sh.transform:
                x1, y1 = sh.transform.transform_point(x1, y1)
                x2, y2 = sh.transform.transform_point(x2, y2)
            pygame.draw.line(self._surface, c, (int(round(x1)), int(round(y1))), (int(round(x2)), int(round(y2))), width=lw)

        elif kind == "custom":
            contours = kw.get("contours") or ([kw["points"]] if "points" in kw else [])
            transformed_polys: list[list[tuple[float, float]]] = []
            for poly in contours:
                if len(poly) == 0:
                    continue
                if isinstance(poly[0], (int, float)):
                    raw_pts = [(float(poly[i]), float(poly[i + 1])) for i in range(0, len(poly) - 1, 2)]
                else:
                    raw_pts = [(float(p[0]), float(p[1])) for p in poly]
                if sh.transform:
                    raw_pts = [sh.transform.transform_point(px, py) for px, py in raw_pts]
                if len(raw_pts) >= 2:
                    transformed_polys.append(raw_pts)

            if not transformed_polys:
                return

            if len(transformed_polys) == 1 or sw > 0:
                for raw_pts in transformed_polys:
                    pts = [(int(round(px)), int(round(py))) for px, py in raw_pts]
                    if len(pts) >= 3:
                        pygame.draw.polygon(self._surface, c, pts, width=sw)
                    elif len(pts) == 2:
                        pygame.draw.line(self._surface, c, pts[0], pts[1], width=max(1, sw))
            else:
                all_x = [px for poly in transformed_polys for px, _ in poly]
                all_y = [py for poly in transformed_polys for _, py in poly]
                min_x = int(math.floor(min(all_x))) - 1
                min_y = int(math.floor(min(all_y))) - 1
                bw = max(1, int(math.ceil(max(all_x))) - min_x + 2)
                bh = max(1, int(math.ceil(max(all_y))) - min_y + 2)
                tmp = pygame.Surface((bw, bh), pygame.SRCALPHA)

                def _signed_area(pts_list: list[tuple[float, float]]) -> float:
                    n = len(pts_list)
                    return sum(
                        pts_list[i][0] * pts_list[(i + 1) % n][1] - pts_list[(i + 1) % n][0] * pts_list[i][1]
                        for i in range(n)
                    )

                outer_sign = 1 if _signed_area(transformed_polys[0]) >= 0 else -1
                for raw_pts in transformed_polys:
                    if len(raw_pts) < 3:
                        continue
                    sign = 1 if _signed_area(raw_pts) >= 0 else -1
                    fill_col = c if sign == outer_sign else (0, 0, 0, 0)
                    local_pts = [(int(round(px)) - min_x, int(round(py)) - min_y) for px, py in raw_pts]
                    pygame.draw.polygon(tmp, fill_col, local_pts)
                self._surface.blit(tmp, (min_x, min_y))

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
        if (
            len(args) >= 2
            and hasattr(args[0], "__len__")
            and len(args[0]) >= 4
            and hasattr(args[1], "__len__")
            and len(args[1]) >= 4
        ):
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
        advance_cursor = False
        if not args:
            x, y = int(round(self.cursor.x)), int(round(self.cursor.y))
            advance_cursor = True
        elif isinstance(args[0], rect):
            x, y = int(round(args[0].x)), int(round(args[0].y))
        elif isinstance(args[0], (vec2, tuple, list)):
            x, y = int(round(args[0][0])), int(round(args[0][1]))
        elif len(args) >= 2:
            x, y = int(round(args[0])), int(round(args[1]))
        else:
            return

        size = kwargs.get("font_size")
        if size is None:
            if isinstance(args[0], (rect, vec2, tuple, list)):
                if len(args) >= 2 and isinstance(args[1], (int, float)):
                    size = int(round(args[1]))
            elif len(args) >= 3 and isinstance(args[2], (int, float)):
                size = int(round(args[2]))
        font_obj = _load_sys_font(int(round(size))) if size else self.font._font

        if len(args) >= 1 and isinstance(args[0], rect) and args[0].w > 0:
            max_w = int(round(args[0].w))
            words = str(msg).split(" ")
            lines: list[str] = []
            cur = ""
            for word in words:
                test = f"{cur} {word}".strip() if cur else word
                if font_obj.size(test)[0] <= max_w or not cur:
                    cur = test
                else:
                    lines.append(cur)
                    cur = word
            if cur:
                lines.append(cur)
            line_h = font_obj.get_linesize()
            for i, line_str in enumerate(lines):
                rendered = font_obj.render(line_str, True, c)
                if self.alpha < 255:
                    rendered.set_alpha(self.alpha)
                self._surface.blit(rendered, (x, y + i * line_h))
            return

        rendered = font_obj.render(str(msg), True, c) if size else self.font.render(str(msg), c)
        if self.alpha < 255:
            rendered.set_alpha(self.alpha)
        self._surface.blit(rendered, (x, y))
        if advance_cursor:
            self.cursor = vec2(self.cursor.x, self.cursor.y + font_obj.get_linesize())

    def measure_text(self, text: str, font_size: int | None = None, *args, **kwargs) -> tuple[int, int]:
        if font_size:
            f = _load_sys_font(int(round(font_size)))
            return f.size(str(text))
        return self.font.measure_text(str(text))


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


class Screen(Image):
    pass


image = Image

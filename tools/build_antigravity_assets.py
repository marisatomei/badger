#!/usr/bin/env python3
"""Build the Robotized Antigravity Icon offline character pack and launcher icon."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


OUTPUT = Path(__file__).resolve().parents[1] / "badge/apps/Antigravity"
SIZE = (192, 180)
MAX_BUNDLE_BYTES = 3_000_000
TRACKS = ("left", "right", "up", "down", "surprise", "working", "attention", "complete")


def quadratic_bezier(p0, p1, p2, steps=16):
    """Generate points along a quadratic Bezier curve."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        it = 1.0 - t
        x = it * it * p0[0] + 2 * it * t * p1[0] + t * t * p2[0]
        y = it * it * p0[1] + 2 * it * t * p1[1] + t * t * p2[1]
        points.append((x, y))
    return points


def get_spark_polygon(cx, cy, r, waist_ratio=0.32, waist_offset=0.0):
    """Generate the boundary points for the Antigravity 4-pointed spark star."""
    # 4 Tips
    top = (cx, cy - r)
    right = (cx + r, cy)
    bottom = (cx, cy + r)
    left = (cx - r, cy)

    # 4 Inner concave control points (waist)
    c_dist = r * waist_ratio
    c_tr = (cx + c_dist, cy - c_dist + waist_offset)
    c_br = (cx + c_dist, cy + c_dist + waist_offset)
    c_bl = (cx - c_dist, cy + c_dist + waist_offset)
    c_tl = (cx - c_dist, cy - c_dist + waist_offset)

    pts = []
    pts.extend(quadratic_bezier(top, c_tr, right))
    pts.extend(quadratic_bezier(right, c_br, bottom)[1:])
    pts.extend(quadratic_bezier(bottom, c_bl, left)[1:])
    pts.extend(quadratic_bezier(left, c_tl, top)[1:-1])
    return pts


def draw_antigravity_frame(track, frame_idx, total_frames=12):
    """Render a single frame of the Robotized Antigravity Mascot on a 192x180 RGB canvas."""
    scale = 2
    w, h = SIZE[0] * scale, SIZE[1] * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Center base
    cx, cy = (96 * scale), (82 * scale)

    # Animation progress (0.0 to 1.0)
    t = frame_idx / float(max(1, total_frames - 1))

    # Mood-specific variables
    eye_color = (66, 195, 255)       # Cyan / Google Blue LED
    visor_glow = (30, 80, 160)
    ring_color = (0, 210, 255)
    tip_glow = (100, 200, 255)
    body_shift_x = 0
    body_shift_y = 0
    body_tilt = 0.0
    eye_look_x = 0
    eye_look_y = 0
    eye_state = "open"
    star_scale = 1.0
    ring_phase = 0.0
    alert_symbol = None
    sparkle_burst = False

    if track == "neutral":
        # Subtle zero-gravity float
        body_shift_y = math.sin(t * math.pi * 2) * 2.5 * scale
    elif track.startswith("blink-"):
        level = int(track.split("-")[1])
        eye_state = f"blink_{level}"
    elif track == "left":
        body_shift_x = -math.sin(t * math.pi) * 8 * scale
        eye_look_x = -math.sin(t * math.pi) * 7 * scale
        body_tilt = -math.sin(t * math.pi) * 0.08
    elif track == "right":
        body_shift_x = math.sin(t * math.pi) * 8 * scale
        eye_look_x = math.sin(t * math.pi) * 7 * scale
        body_tilt = math.sin(t * math.pi) * 0.08
    elif track == "up":
        body_shift_y = -math.sin(t * math.pi) * 8 * scale
        eye_look_y = -math.sin(t * math.pi) * 6 * scale
    elif track == "down":
        body_shift_y = math.sin(t * math.pi) * 8 * scale
        eye_look_y = math.sin(t * math.pi) * 6 * scale
    elif track == "surprise":
        # Quick levitation hop and wide eyes
        body_shift_y = -math.sin(t * math.pi) * 14 * scale
        star_scale = 1.0 + math.sin(t * math.pi) * 0.08
        eye_state = "wide"
        tip_glow = (255, 220, 100)
        ring_color = (120, 230, 255)
        sparkle_burst = True
    elif track == "working":
        # Active processing: rotating anti-gravity ring, focused eyes, pulsing energy tips
        body_shift_y = math.sin(frame_idx * 0.5) * 2.5 * scale
        ring_phase = frame_idx * (math.pi / 6)
        eye_state = "focused"
        ring_color = (66, 133, 244)
        tip_glow = (120, 180, 255) if (frame_idx % 2 == 0) else (200, 230, 255)
    elif track == "attention":
        # Amber warning glow, inquisitive tilt
        body_shift_y = math.sin(frame_idx * 0.8) * 3 * scale
        body_shift_x = math.sin(frame_idx * 0.4) * 2 * scale
        body_tilt = 0.12 * math.sin(frame_idx * 0.6)
        eye_color = (255, 180, 0)
        visor_glow = (180, 110, 0)
        ring_color = (255, 160, 0)
        tip_glow = (255, 210, 50)
        alert_symbol = "!"
    elif track == "complete":
        # Cheerful bounce, happy emerald glow
        body_shift_y = -abs(math.sin(t * math.pi * 2)) * 12 * scale
        eye_color = (76, 175, 80)
        visor_glow = (27, 94, 32)
        ring_color = (102, 187, 106)
        tip_glow = (165, 214, 167)
        eye_state = "happy"
        sparkle_burst = True

    bx = cx + body_shift_x
    by = cy + body_shift_y

    # 1. Subtle anti-gravity ground shadow
    shadow_w = 34 * scale
    shadow_h = 7 * scale
    shadow_y = (136 * scale)
    draw.ellipse([cx - shadow_w, shadow_y - shadow_h, cx + shadow_w, shadow_y + shadow_h],
                 fill=(15, 25, 45, 160))

    # 2. Back half of Anti-gravity Propulsion Ring (orbits beneath bottom tip)
    ring_rx = 36 * scale
    ring_ry = 10 * scale
    ring_cy = by + (32 * scale)

    for angle_deg in range(180, 360, 6):
        rad = math.radians(angle_deg) + ring_phase
        rx = bx + ring_rx * math.cos(rad)
        ry = ring_cy + ring_ry * math.sin(rad)
        draw.ellipse([rx - 2.5 * scale, ry - 2.5 * scale, rx + 2.5 * scale, ry + 2.5 * scale],
                     fill=(*ring_color, 110))

    # 3. Robotized Antigravity Star Chassis
    star_r = (48 * scale) * star_scale

    # Helper to rotate polygon if tilted
    def apply_tilt(points, center_x, center_y, angle):
        if abs(angle) < 0.001:
            return points
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        res = []
        for px, py in points:
            dx = px - center_x
            dy = py - center_y
            rx = center_x + dx * cos_a - dy * sin_a
            ry = center_y + dx * sin_a + dy * cos_a
            res.append((rx, ry))
        return res

    # Outer armor hull (Google dark slate/metallic)
    outer_poly = get_spark_polygon(bx, by, star_r, waist_ratio=0.34)
    outer_poly = apply_tilt(outer_poly, bx, by, body_tilt)
    draw.polygon(outer_poly, fill=(24, 32, 46, 255), outline=(70, 105, 155, 255))

    # Inner armor plate with bevel
    inner_poly = get_spark_polygon(bx, by, star_r * 0.90, waist_ratio=0.33)
    inner_poly = apply_tilt(inner_poly, bx, by, body_tilt)
    draw.polygon(inner_poly, fill=(32, 44, 64, 255), outline=(90, 130, 185, 255))

    # Star tip cybernetic nodes / thruster caps
    tip_coords = [
        (bx, by - star_r),       # Top
        (bx + star_r, by),       # Right
        (bx, by + star_r),       # Bottom
        (bx - star_r, by),       # Left
    ]
    tip_coords = apply_tilt(tip_coords, bx, by, body_tilt)

    for tx, ty in tip_coords:
        tr = 4.0 * scale
        draw.ellipse([tx - tr, ty - tr, tx + tr, ty + tr],
                     fill=tip_glow, outline=(255, 255, 255, 220), width=scale)

    # Waist cybernetic rivets/nodes
    waist_coords = [
        (bx + star_r * 0.33, by - star_r * 0.33),
        (bx + star_r * 0.33, by + star_r * 0.33),
        (bx - star_r * 0.33, by + star_r * 0.33),
        (bx - star_r * 0.33, by - star_r * 0.33),
    ]
    waist_coords = apply_tilt(waist_coords, bx, by, body_tilt)
    for wx, wy in waist_coords:
        wr = 2.0 * scale
        draw.ellipse([wx - wr, wy - wr, wx + wr, wy + wr], fill=(66, 133, 244, 200))

    # 4. Front half of Anti-gravity Propulsion Ring (crosses over bottom point)
    for angle_deg in range(0, 185, 6):
        rad = math.radians(angle_deg) + ring_phase
        rx = bx + ring_rx * math.cos(rad)
        ry = ring_cy + ring_ry * math.sin(rad)
        draw.ellipse([rx - 2.5 * scale, ry - 2.5 * scale, rx + 2.5 * scale, ry + 2.5 * scale],
                     fill=(*ring_color, 230))

    # 5. Center Robot Face / Tinted Visor
    visor_w = 23 * scale
    visor_h = 14 * scale
    draw.rounded_rectangle([bx - visor_w, by - visor_h, bx + visor_w, by + visor_h],
                           radius=9 * scale, fill=(10, 14, 22, 255),
                           outline=visor_glow, width=2 * scale)

    # 6. Expressive LED Eyes inside Visor
    eye_offset_x = 9 * scale
    lex = bx - eye_offset_x + eye_look_x
    rex = bx + eye_offset_x + eye_look_x
    ey = by + eye_look_y

    if eye_state == "wide":
        ew, eh = 7 * scale, 9 * scale
        draw.ellipse([lex - ew, ey - eh, lex + ew, ey + eh], fill=eye_color)
        draw.ellipse([rex - ew, ey - eh, rex + ew, ey + eh], fill=eye_color)
        draw.ellipse([lex - 2 * scale, ey - 3 * scale, lex + 2 * scale, ey + scale], fill=(255, 255, 255))
        draw.ellipse([rex - 2 * scale, ey - 3 * scale, rex + 2 * scale, ey + scale], fill=(255, 255, 255))
    elif eye_state == "focused":
        # Scanning digital visor slits
        draw.rounded_rectangle([lex - 6 * scale, ey - 2.5 * scale, lex + 6 * scale, ey + 2.5 * scale],
                               radius=scale, fill=eye_color)
        draw.rounded_rectangle([rex - 6 * scale, ey - 2.5 * scale, rex + 6 * scale, ey + 2.5 * scale],
                               radius=scale, fill=eye_color)
    elif eye_state == "happy":
        # Cheerful happy eyes ^ ^
        for ex in (lex, rex):
            draw.arc([ex - 5 * scale, ey - 5 * scale, ex + 5 * scale, ey + 3 * scale],
                     start=190, end=350, fill=eye_color, width=int(2 * scale))
    elif eye_state.startswith("blink_"):
        lvl = int(eye_state.split("_")[1])
        height_map = {1: 6 * scale, 2: 3.5 * scale, 3: 2 * scale, 4: 1 * scale}
        eh = height_map.get(lvl, 1 * scale)
        ew = 5.5 * scale
        draw.rounded_rectangle([lex - ew, ey - eh, lex + ew, ey + eh], radius=scale, fill=eye_color)
        draw.rounded_rectangle([rex - ew, ey - eh, rex + ew, ey + eh], radius=scale, fill=eye_color)
    else:  # Normal open eyes
        ew, eh = 5.5 * scale, 6.5 * scale
        draw.ellipse([lex - ew, ey - eh, lex + ew, ey + eh], fill=eye_color)
        draw.ellipse([rex - ew, ey - eh, rex + ew, ey + eh], fill=eye_color)
        draw.ellipse([lex - scale, ey - 2.5 * scale, lex + 1.5 * scale, ey], fill=(255, 255, 255, 220))
        draw.ellipse([rex - scale, ey - 2.5 * scale, rex + 1.5 * scale, ey], fill=(255, 255, 255, 220))

    # 7. Sparkle burst or alert overlay
    if sparkle_burst:
        for angle in (0.2, 1.8, 3.4, 4.8):
            sp_x = bx + math.cos(angle) * (star_r + 9 * scale)
            sp_y = by + math.sin(angle) * (star_r + 9 * scale)
            draw.ellipse([sp_x - 2 * scale, sp_y - 2 * scale, sp_x + 2 * scale, sp_y + 2 * scale],
                         fill=(255, 255, 255, 230))

    if alert_symbol:
        draw.text((bx + 28 * scale, by - 26 * scale), alert_symbol, fill=(255, 200, 0), font=None)

    # Downsample back to target 192x180 RGB canvas
    final_img = Image.new("RGB", SIZE, (0, 0, 0))
    downsampled = img.resize(SIZE, Image.Resampling.LANCZOS)
    final_img.paste(downsampled, (0, 0), downsampled.convert("RGBA"))
    return final_img


def build(output_dir):
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    jobs = [("neutral", "neutral", 0)]
    for lvl in range(1, 5):
        jobs.append((f"blink-{lvl}", f"blink-{lvl}", 0))

    for track in TRACKS:
        for idx in range(12):
            jobs.append((f"{track}-{idx:02d}", track, idx))

    files_meta = []
    print(f"Generating {len(jobs)} Robotized Antigravity Mascot frames...")

    for name, track, idx in jobs:
        frame = draw_antigravity_frame(track, idx)
        out_path = assets_dir / f"{name}.png"
        frame.save(out_path, optimize=True)
        raw_bytes = out_path.read_bytes()
        files_meta.append({
            "file": f"{name}.png",
            "source": f"procedural/robot_spark/{name}",
            "sha256": hashlib.sha256(raw_bytes).hexdigest()
        })

    # Generate 24x24 icon.png for launcher (robotized Antigravity star)
    icon_scale = 4
    icon_w = 24 * icon_scale
    icon_img = Image.new("RGBA", (icon_w, icon_w), (0, 0, 0, 255))
    idraw = ImageDraw.Draw(icon_img)
    icx, icy = icon_w // 2, icon_w // 2

    # Star shape for icon
    icon_r = 10 * icon_scale
    icon_star = get_spark_polygon(icx, icy, icon_r, waist_ratio=0.34)
    idraw.polygon(icon_star, fill=(32, 44, 64), outline=(90, 130, 185), width=icon_scale)

    # Mini glowing tips
    for tx, ty in [(icx, icy - icon_r), (icx + icon_r, icy), (icx, icy + icon_r), (icx - icon_r, icy)]:
        idraw.ellipse([tx - 1.5 * icon_scale, ty - 1.5 * icon_scale,
                       tx + 1.5 * icon_scale, ty + 1.5 * icon_scale], fill=(100, 200, 255))

    # Center mini visor
    vw, vh = 5 * icon_scale, 3.5 * icon_scale
    idraw.rounded_rectangle([icx - vw, icy - vh, icx + vw, icy + vh],
                            radius=2 * icon_scale, fill=(10, 14, 22), outline=(30, 80, 160))
    # Eyes
    idraw.ellipse([icx - 3 * icon_scale, icy - icon_scale, icx - icon_scale, icy + icon_scale],
                  fill=(66, 195, 255))
    idraw.ellipse([icx + icon_scale, icy - icon_scale, icx + 3 * icon_scale, icy + icon_scale],
                  fill=(66, 195, 255))

    icon_final = Image.new("RGB", (24, 24), (0, 0, 0))
    icon_downsampled = icon_img.resize((24, 24), Image.Resampling.LANCZOS)
    icon_final.paste(icon_downsampled, (0, 0), icon_downsampled.convert("RGBA"))
    icon_path = output_dir / "icon.png"
    icon_final.save(icon_path, optimize=True)

    # Write LICENSE.txt and sources.json
    (assets_dir / "LICENSE.txt").write_text(
        "MIT License\n\nCopyright (c) 2026 Antigravity Badge Contributors\n\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        "of this software and associated documentation files (the \"Software\"), to deal\n"
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n"
    )

    metadata = {
        "repository": "https://github.com/google-antigravity/antigravity",
        "size": list(SIZE),
        "frames_per_track": 12,
        "conversion": "Robotized Antigravity Spark Star mascot, RGB 192x180; Pillow",
        "files": files_meta
    }
    (assets_dir / "sources.json").write_text(json.dumps(metadata, indent=2) + "\n")

    total_bytes = sum(p.stat().st_size for p in assets_dir.iterdir() if p.is_file())
    print(f"Generated {len(files_meta)} frames, {total_bytes} bytes in {assets_dir}")
    if total_bytes > MAX_BUNDLE_BYTES:
        raise ValueError(f"Assets exceed budget: {total_bytes} > {MAX_BUNDLE_BYTES}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    build(parser.parse_args().output)

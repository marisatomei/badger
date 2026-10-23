#!/usr/bin/env python3
"""Build the Antigravity offline character pack and icon for the hardware badge."""

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


def draw_antigravity_frame(track, frame_idx, total_frames=12):
    """Render a single frame of the Antigravity companion mascot on a 192x180 RGB canvas."""
    # Work on a 2x supersampled canvas for ultra-crisp antialiasing, then downsample
    scale = 2
    w, h = SIZE[0] * scale, SIZE[1] * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Base bot parameters (scaled)
    cx, cy = (96 * scale), (82 * scale)

    # Animation progress (0.0 to 1.0)
    t = frame_idx / float(max(1, total_frames - 1))

    # Mood-specific overrides
    eye_color = (66, 165, 245)      # Google blue / cyan
    visor_glow = (30, 80, 160)
    ring_color = (0, 200, 255)
    body_shift_x = 0
    body_shift_y = 0
    ring_tilt = 0.0
    eye_look_x = 0
    eye_look_y = 0
    eye_state = "open"  # "open", "wide", "wink", "happy", "focused", "blink"
    spark_color = (130, 200, 255)
    alert_symbol = None
    ring_phase = 0.0

    if track == "neutral":
        body_shift_y = math.sin(t * math.pi * 2) * 2 * scale
    elif track.startswith("blink-"):
        level = int(track.split("-")[1])
        eye_state = f"blink_{level}"
    elif track == "left":
        body_shift_x = -math.sin(t * math.pi) * 8 * scale
        eye_look_x = -math.sin(t * math.pi) * 6 * scale
        ring_tilt = math.sin(t * math.pi) * 0.15
    elif track == "right":
        body_shift_x = math.sin(t * math.pi) * 8 * scale
        eye_look_x = math.sin(t * math.pi) * 6 * scale
        ring_tilt = -math.sin(t * math.pi) * 0.15
    elif track == "up":
        body_shift_y = -math.sin(t * math.pi) * 8 * scale
        eye_look_y = -math.sin(t * math.pi) * 6 * scale
    elif track == "down":
        body_shift_y = math.sin(t * math.pi) * 8 * scale
        eye_look_y = math.sin(t * math.pi) * 6 * scale
    elif track == "surprise":
        body_shift_y = -math.sin(t * math.pi) * 12 * scale
        eye_state = "wide"
        spark_color = (255, 220, 100)
        ring_color = (100, 220, 255)
    elif track == "working":
        # Hover bounce + ring rotation + focused eyes
        body_shift_y = math.sin(frame_idx * 0.5) * 3 * scale
        ring_phase = frame_idx * (math.pi / 6)
        eye_state = "focused"
        ring_color = (66, 133, 244)
    elif track == "attention":
        # Amber warning glow, slight alert tilt
        body_shift_y = math.sin(frame_idx * 0.8) * 4 * scale
        body_shift_x = math.sin(frame_idx * 0.4) * 2 * scale
        eye_color = (255, 180, 0)
        visor_glow = (180, 110, 0)
        ring_color = (255, 160, 0)
        spark_color = (255, 215, 0)
        alert_symbol = "!"
    elif track == "complete":
        # Happy emerald glow, celebratory bounce
        body_shift_y = -abs(math.sin(t * math.pi * 2)) * 10 * scale
        eye_color = (76, 175, 80)
        visor_glow = (27, 94, 32)
        ring_color = (102, 187, 106)
        spark_color = (129, 199, 132)
        eye_state = "happy"

    bx = cx + body_shift_x
    by = cy + body_shift_y

    # 1. Shadow / Anti-gravity ground distortion (subtle)
    shadow_w = 40 * scale
    shadow_h = 8 * scale
    shadow_y = (135 * scale)
    draw.ellipse([cx - shadow_w, shadow_y - shadow_h, cx + shadow_w, shadow_y + shadow_h],
                 fill=(15, 25, 45, 180))

    # 2. Back of Anti-gravity Propulsion Ring
    ring_rx = 48 * scale
    ring_ry = 14 * scale
    ring_cy = by + (26 * scale)

    # Draw back half of ring
    for angle_deg in range(180, 360, 5):
        rad = math.radians(angle_deg) + ring_phase
        rx = bx + ring_rx * math.cos(rad)
        ry = ring_cy + ring_ry * math.sin(rad) + (rx - bx) * ring_tilt
        draw.ellipse([rx - 3 * scale, ry - 3 * scale, rx + 3 * scale, ry + 3 * scale],
                     fill=(*ring_color, 120))

    # 3. Floating Body (Sleek Anti-gravity Orb / Drone)
    body_r = 34 * scale
    # Outer metallic body
    draw.ellipse([bx - body_r, by - body_r, bx + body_r, by + body_r],
                 fill=(28, 36, 52, 255), outline=(90, 120, 165, 255), width=2 * scale)
    # Highlight reflection on top of sphere
    highlight_r = 18 * scale
    draw.ellipse([bx - highlight_r, by - body_r + 4 * scale,
                  bx + highlight_r, by - body_r + (14 * scale)],
                 fill=(140, 170, 215, 100))

    # 4. Visor Screen (Pill shape on the face)
    visor_w = 26 * scale
    visor_h = 16 * scale
    visor_y = by - (2 * scale)
    draw.rounded_rectangle([bx - visor_w, visor_y - visor_h, bx + visor_w, visor_y + visor_h],
                           radius=10 * scale, fill=(10, 14, 22, 255),
                           outline=visor_glow, width=2 * scale)

    # 5. Visor Eyes
    eye_offset_x = 10 * scale
    lex = bx - eye_offset_x + eye_look_x
    rex = bx + eye_offset_x + eye_look_x
    ey = visor_y + eye_look_y

    if eye_state == "wide":
        ew, eh = 8 * scale, 10 * scale
        draw.ellipse([lex - ew, ey - eh, lex + ew, ey + eh], fill=eye_color)
        draw.ellipse([rex - ew, ey - eh, rex + ew, ey + eh], fill=eye_color)
        # Inner white pupil reflection
        draw.ellipse([lex - 2 * scale, ey - 3 * scale, lex + 2 * scale, ey + scale], fill=(255, 255, 255))
        draw.ellipse([rex - 2 * scale, ey - 3 * scale, rex + 2 * scale, ey + scale], fill=(255, 255, 255))
    elif eye_state == "focused":
        # Narrow horizontal focused slits
        draw.rounded_rectangle([lex - 7 * scale, ey - 3 * scale, lex + 7 * scale, ey + 3 * scale],
                               radius=2 * scale, fill=eye_color)
        draw.rounded_rectangle([rex - 7 * scale, ey - 3 * scale, rex + 7 * scale, ey + 3 * scale],
                               radius=2 * scale, fill=eye_color)
    elif eye_state == "happy":
        # Cheerful inverted archs ^ ^
        for ex in (lex, rex):
            draw.arc([ex - 6 * scale, ey - 6 * scale, ex + 6 * scale, ey + 4 * scale],
                     start=190, end=350, fill=eye_color, width=3 * scale)
    elif eye_state.startswith("blink_"):
        lvl = int(eye_state.split("_")[1])
        height_map = {1: 7 * scale, 2: 4 * scale, 3: 2 * scale, 4: 1 * scale}
        eh = height_map.get(lvl, 1 * scale)
        ew = 6 * scale
        draw.rounded_rectangle([lex - ew, ey - eh, lex + ew, ey + eh], radius=1 * scale, fill=eye_color)
        draw.rounded_rectangle([rex - ew, ey - eh, rex + ew, ey + eh], radius=1 * scale, fill=eye_color)
    else:  # Normal open eyes
        ew, eh = 6 * scale, 7 * scale
        draw.ellipse([lex - ew, ey - eh, lex + ew, ey + eh], fill=eye_color)
        draw.ellipse([rex - ew, ey - eh, rex + ew, ey + eh], fill=eye_color)
        # Highlights
        draw.ellipse([lex - scale, ey - 3 * scale, lex + 2 * scale, ey], fill=(255, 255, 255, 220))
        draw.ellipse([rex - scale, ey - 3 * scale, rex + 2 * scale, ey], fill=(255, 255, 255, 220))

    # 6. Front of Anti-gravity Propulsion Ring (overlaps front of body)
    for angle_deg in range(0, 185, 5):
        rad = math.radians(angle_deg) + ring_phase
        rx = bx + ring_rx * math.cos(rad)
        ry = ring_cy + ring_ry * math.sin(rad) + (rx - bx) * ring_tilt
        draw.ellipse([rx - 3 * scale, ry - 3 * scale, rx + 3 * scale, ry + 3 * scale],
                     fill=(*ring_color, 240))

    # 7. Antenna and Glowing Spark Orb (Top)
    ant_base_y = by - body_r
    ant_top_y = ant_base_y - (12 * scale)
    draw.line([bx, ant_base_y, bx, ant_top_y], fill=(90, 120, 165), width=2 * scale)
    # Glowing top spark orb
    spark_r = 5 * scale
    draw.ellipse([bx - spark_r, ant_top_y - spark_r, bx + spark_r, ant_top_y + spark_r],
                 fill=spark_color, outline=(255, 255, 255), width=scale)

    # 8. Alert symbol if active
    if alert_symbol:
        draw.text((bx + 26 * scale, by - 24 * scale), alert_symbol, fill=(255, 200, 0), font=None)

    # Downsample back to target size with Lanczos antialiasing
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
    print(f"Generating {len(jobs)} Antigravity mascot frames...")

    for name, track, idx in jobs:
        frame = draw_antigravity_frame(track, idx)
        out_path = assets_dir / f"{name}.png"
        frame.save(out_path, optimize=True)
        raw_bytes = out_path.read_bytes()
        files_meta.append({
            "file": f"{name}.png",
            "source": f"procedural/{track}/{name}",
            "sha256": hashlib.sha256(raw_bytes).hexdigest()
        })

    # Generate 24x24 icon.png for launcher
    # Render crisp Antigravity bot icon
    icon_scale = 4
    icon_img = Image.new("RGBA", (24 * icon_scale, 24 * icon_scale), (0, 0, 0, 255))
    idraw = ImageDraw.Draw(icon_img)
    icx, icy = 12 * icon_scale, 13 * icon_scale
    # Body
    ir = 7 * icon_scale
    idraw.ellipse([icx - ir, icy - ir, icx + ir, icy + ir],
                  fill=(28, 36, 52), outline=(90, 120, 165), width=icon_scale)
    # Visor
    idraw.rounded_rectangle([icx - 5 * icon_scale, icy - 2 * icon_scale,
                             icx + 5 * icon_scale, icy + 3 * icon_scale],
                            radius=2 * icon_scale, fill=(10, 14, 22), outline=(30, 80, 160))
    # Eyes
    idraw.ellipse([icx - 3 * icon_scale, icy - icon_scale,
                   icx - icon_scale, icy + icon_scale], fill=(66, 165, 245))
    idraw.ellipse([icx + icon_scale, icy - icon_scale,
                   icx + 3 * icon_scale, icy + icon_scale], fill=(66, 165, 245))
    # Antenna
    idraw.line([icx, icy - ir, icx, icy - ir - 3 * icon_scale], fill=(90, 120, 165), width=icon_scale)
    idraw.ellipse([icx - icon_scale, icy - ir - 5 * icon_scale,
                   icx + icon_scale, icy - ir - 3 * icon_scale], fill=(130, 200, 255))

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
        "conversion": "Antialiased procedural mascot generation, RGB 192x180; Pillow",
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

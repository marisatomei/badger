#!/usr/bin/env python3
"""Build the Robotized Antigravity Arch offline character pack and launcher icon."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw


OUTPUT = Path(__file__).resolve().parents[1] / "badge/apps/Antigravity"
LOGO_PATH = Path(__file__).resolve().parent / "antigravity_logo.png"
SIZE = (192, 180)
MAX_BUNDLE_BYTES = 3_000_000
TRACKS = ("left", "right", "up", "down", "surprise", "working", "attention", "complete")


def draw_antigravity_frame(base_logo, track, frame_idx, total_frames=12):
    """Render a single frame of the Robotized Antigravity Arch mascot on a 192x180 RGB canvas."""
    scale = 2
    w, h = SIZE[0] * scale, SIZE[1] * scale
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 255))

    # Base parameters for the arch body
    logo_w, logo_h = int(126 * scale), int(126 * scale)
    base_x = (w - logo_w) // 2
    base_y = int(24 * scale)

    # Animation progress (0.0 to 1.0)
    t = frame_idx / float(max(1, total_frames - 1))

    # Mood-specific variables
    eye_color = (66, 195, 255)       # Cyan LED
    visor_glow = (60, 110, 190)
    thruster_color = (0, 210, 255)
    body_shift_x = 0
    body_shift_y = 0
    body_tilt = 0.0
    eye_look_x = 0
    eye_look_y = 0
    eye_state = "open"
    squish_x = 1.0
    squish_y = 1.0
    alert_symbol = None
    sparkle_burst = False
    thruster_active = True

    if track == "neutral":
        # Gentle zero-gravity hover
        body_shift_y = math.sin(t * math.pi * 2) * 2.5 * scale
    elif track.startswith("blink-"):
        level = int(track.split("-")[1])
        eye_state = f"blink_{level}"
    elif track == "left":
        body_shift_x = -math.sin(t * math.pi) * 8 * scale
        eye_look_x = -math.sin(t * math.pi) * 8 * scale
        body_tilt = -math.sin(t * math.pi) * 0.08
    elif track == "right":
        body_shift_x = math.sin(t * math.pi) * 8 * scale
        eye_look_x = math.sin(t * math.pi) * 8 * scale
        body_tilt = math.sin(t * math.pi) * 0.08
    elif track == "up":
        body_shift_y = -math.sin(t * math.pi) * 8 * scale
        eye_look_y = -math.sin(t * math.pi) * 6 * scale
    elif track == "down":
        body_shift_y = math.sin(t * math.pi) * 8 * scale
        eye_look_y = math.sin(t * math.pi) * 6 * scale
    elif track == "surprise":
        # Upward startled hop with squish/stretch
        body_shift_y = -math.sin(t * math.pi) * 14 * scale
        squish_y = 1.0 + math.sin(t * math.pi) * 0.08
        squish_x = 1.0 - math.sin(t * math.pi) * 0.06
        eye_state = "wide"
        thruster_color = (120, 230, 255)
        sparkle_burst = True
    elif track == "working":
        # Active processing bounce with pulsing thrusters
        body_shift_y = math.sin(frame_idx * 0.6) * 3 * scale
        eye_state = "focused"
        thruster_color = (66, 133, 244) if (frame_idx % 2 == 0) else (140, 220, 255)
    elif track == "attention":
        # Amber warning glow, inquisitive tilt
        body_shift_y = math.sin(frame_idx * 0.8) * 3.5 * scale
        body_shift_x = math.sin(frame_idx * 0.4) * 2 * scale
        body_tilt = 0.10 * math.sin(frame_idx * 0.6)
        eye_color = (255, 180, 0)
        visor_glow = (200, 120, 0)
        thruster_color = (255, 160, 0)
        alert_symbol = "!"
    elif track == "complete":
        # Celebratory hop, emerald green glow
        body_shift_y = -abs(math.sin(t * math.pi * 2)) * 13 * scale
        squish_y = 1.0 + math.sin(t * math.pi * 2) * 0.06
        eye_color = (76, 175, 80)
        visor_glow = (30, 110, 40)
        thruster_color = (102, 187, 106)
        eye_state = "happy"
        sparkle_burst = True

    # 1. Subtle anti-gravity ground shadow
    shadow_w = 42 * scale
    shadow_h = 7 * scale
    shadow_y = int(140 * scale)
    sdraw = ImageDraw.Draw(canvas)
    sdraw.ellipse([w // 2 - shadow_w, shadow_y - shadow_h, w // 2 + shadow_w, shadow_y + shadow_h],
                 fill=(15, 25, 45, 150))

    # 2. Transform and draw Antigravity Arch Body
    curr_w = int(logo_w * squish_x)
    curr_h = int(logo_h * squish_y)
    body_img = base_logo.resize((curr_w, curr_h), Image.Resampling.LANCZOS)

    if abs(body_tilt) > 0.01:
        body_img = body_img.rotate(math.degrees(body_tilt), resample=Image.Resampling.BICUBIC, expand=True)

    lx = int(base_x + body_shift_x + (logo_w - body_img.width) / 2)
    ly = int(base_y + body_shift_y + (logo_h - body_img.height) / 2)
    canvas.alpha_composite(body_img, (lx, ly))

    # Center of visor (relative to scaled body)
    vx = lx + body_img.width // 2
    vy = ly + int(46 * scale * squish_y)
    draw = ImageDraw.Draw(canvas)

    # 3. Feet Hover Thrusters (underneath the two arch legs)
    if thruster_active:
        foot_y = ly + int(112 * scale * squish_y)
        left_foot_x = lx + int(14 * scale)
        right_foot_x = lx + body_img.width - int(14 * scale)
        for fx in (left_foot_x, right_foot_x):
            # Glowing oval thruster pulse
            draw.ellipse([fx - 10 * scale, foot_y - 3 * scale,
                          fx + 10 * scale, foot_y + 4 * scale],
                         fill=(*thruster_color, 190))
            draw.ellipse([fx - 5 * scale, foot_y - 1.5 * scale,
                          fx + 5 * scale, foot_y + 2 * scale],
                         fill=(255, 255, 255, 220))

    # 4. Robot Visor (Pill-shaped tinted face)
    vw, vh = int(24 * scale), int(15 * scale)
    # Beveled metallic visor frame
    draw.rounded_rectangle([vx - vw - 2 * scale, vy - vh - 2 * scale,
                            vx + vw + 2 * scale, vy + vh + 2 * scale],
                           radius=9 * scale, fill=(20, 28, 42, 230),
                           outline=(70, 105, 155, 255), width=int(scale))
    # Tinted glass
    draw.rounded_rectangle([vx - vw, vy - vh, vx + vw, vy + vh],
                           radius=7 * scale, fill=(10, 14, 22, 255),
                           outline=visor_glow, width=int(1.5 * scale))

    # 5. Expressive Digital LED Eyes
    eye_offset_x = int(10 * scale)
    lex = vx - eye_offset_x + eye_look_x
    rex = vx + eye_offset_x + eye_look_x
    ey = vy + eye_look_y

    if eye_state == "wide":
        ew, eh = 7 * scale, 9 * scale
        draw.ellipse([lex - ew, ey - eh, lex + ew, ey + eh], fill=eye_color)
        draw.ellipse([rex - ew, ey - eh, rex + ew, ey + eh], fill=eye_color)
        draw.ellipse([lex - 2 * scale, ey - 3 * scale, lex + 2 * scale, ey + scale], fill=(255, 255, 255))
        draw.ellipse([rex - 2 * scale, ey - 3 * scale, rex + 2 * scale, ey + scale], fill=(255, 255, 255))
    elif eye_state == "focused":
        # Scanning laser digital slits
        draw.rounded_rectangle([lex - 6 * scale, ey - 2.5 * scale, lex + 6 * scale, ey + 2.5 * scale],
                               radius=scale, fill=eye_color)
        draw.rounded_rectangle([rex - 6 * scale, ey - 2.5 * scale, rex + 6 * scale, ey + 2.5 * scale],
                               radius=scale, fill=eye_color)
        # Laser scanning wave
        draw.line([vx - vw + 4 * scale, vy, vx + vw - 4 * scale, vy], fill=(*eye_color, 120), width=int(scale))
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
        # Eye pupil highlights
        draw.ellipse([lex - scale, ey - 2.5 * scale, lex + 1.5 * scale, ey], fill=(255, 255, 255, 220))
        draw.ellipse([rex - scale, ey - 2.5 * scale, rex + 1.5 * scale, ey], fill=(255, 255, 255, 220))

    # 6. Sparkle bursts or alert badge
    if sparkle_burst:
        for angle in (0.3, 1.5, 3.2, 4.6):
            sp_x = vx + math.cos(angle) * (vw + 16 * scale)
            sp_y = vy + math.sin(angle) * (vh + 14 * scale)
            draw.ellipse([sp_x - 2 * scale, sp_y - 2 * scale, sp_x + 2 * scale, sp_y + 2 * scale],
                         fill=(255, 255, 255, 230))

    if alert_symbol:
        draw.text((vx + vw + 4 * scale, vy - vh - 6 * scale), alert_symbol, fill=(255, 200, 0), font=None)

    # Downsample back to 192x180 RGB canvas
    final_img = Image.new("RGB", SIZE, (0, 0, 0))
    downsampled = canvas.resize(SIZE, Image.Resampling.LANCZOS)
    final_img.paste(downsampled, (0, 0), downsampled.convert("RGBA"))
    return final_img


def build(output_dir):
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    if not LOGO_PATH.is_file():
        raise FileNotFoundError(f"Missing base logo at {LOGO_PATH}")

    base_logo = Image.open(LOGO_PATH).convert("RGBA")

    jobs = [("neutral", "neutral", 0)]
    for lvl in range(1, 5):
        jobs.append((f"blink-{lvl}", f"blink-{lvl}", 0))

    for track in TRACKS:
        for idx in range(12):
            jobs.append((f"{track}-{idx:02d}", track, idx))

    files_meta = []
    print(f"Generating {len(jobs)} Robotized Antigravity Arch Mascot frames...")

    for name, track, idx in jobs:
        frame = draw_antigravity_frame(base_logo, track, idx)
        out_path = assets_dir / f"{name}.png"
        frame.save(out_path, optimize=True)
        raw_bytes = out_path.read_bytes()
        files_meta.append({
            "file": f"{name}.png",
            "source": f"procedural/antigravity_arch/{name}",
            "sha256": hashlib.sha256(raw_bytes).hexdigest()
        })

    # Generate 24x24 icon.png for launcher
    icon_scale = 4
    icon_w = 24 * icon_scale
    icon_canvas = Image.new("RGBA", (icon_w, icon_w), (0, 0, 0, 255))
    mini_logo = base_logo.resize((int(20 * icon_scale), int(20 * icon_scale)), Image.Resampling.LANCZOS)
    icon_canvas.alpha_composite(mini_logo, (int(2 * icon_scale), int(2 * icon_scale)))

    idraw = ImageDraw.Draw(icon_canvas)
    icx, icy = icon_w // 2, int(9 * icon_scale)
    vw, vh = int(4.5 * icon_scale), int(3 * icon_scale)
    idraw.rounded_rectangle([icx - vw, icy - vh, icx + vw, icy + vh],
                            radius=int(1.5 * icon_scale), fill=(10, 14, 22), outline=(30, 80, 160))
    idraw.ellipse([icx - 2.5 * icon_scale, icy - icon_scale, icx - 0.5 * icon_scale, icy + icon_scale],
                  fill=(66, 195, 255))
    idraw.ellipse([icx + 0.5 * icon_scale, icy - icon_scale, icx + 2.5 * icon_scale, icy + icon_scale],
                  fill=(66, 195, 255))

    icon_final = Image.new("RGB", (24, 24), (0, 0, 0))
    icon_downsampled = icon_canvas.resize((24, 24), Image.Resampling.LANCZOS)
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
        "conversion": "Robotized Antigravity Arch mascot, RGB 192x180; Pillow",
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

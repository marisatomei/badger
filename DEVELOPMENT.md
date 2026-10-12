# Getting Started with Universe 2026 Badge Development

This repository contains the applications, firmware scripts, and hardware documentation for the **GitHub Universe 2026 badge** (a custom derivative of Pimoroni's Tufty 2350 powered by the RP2350B MCU).

---

## Repository Structure

| Path | Purpose |
| --- | --- |
| [`badge/`](./badge/) | **Universe 2026** root filesystem (`/system`), apps, assets, and startup code |
| [`badge/apps/`](./badge/apps/) | All 2026 MicroPython applications |
| [`hardware/`](./hardware/) | RP2350B schematic, GPIO map, and USB serial documentation |
| [`tools/`](./tools/) | Developer CLI helper (`tools/badge.py`) |
| [`tests/`](./tests/) | Test suite for app syntax, icons, and API compliance |
| [`badge25/`](./badge25/) | Archived Universe 2025 badge code, docs, and Pygame simulator |
| [`ir-beacon/`](./ir-beacon/) | IR beacon protocols and scripts |

---

## Quick Start

### 1. Set Up Environment

Python 3.10+ is required. To set up dependencies in a virtual environment:

```bash
# Using Makefile:
make setup

# Or manually:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Validate Codebase & Apps

To verify Python syntax, app structure, icon dimensions (24x24), and check that no legacy 2025 imports or anti-patterns are present:

```bash
make validate
# or run the full test suite:
make test
```

### 3. Create a New Badge App

To scaffold a new 2026 app with a starter frame loop and a generated 24x24 icon:

```bash
make new-app APP=my_game
```

This creates:
```text
badge/apps/my_game/
├── __init__.py      # App entry point with update() loop & logical inputs
├── icon.png         # 24x24 PNG icon for the menu
└── assets/          # Directory for game assets and sprites
```

---

## Universe 2026 Badge Simulator

The repository includes a standalone Pygame simulator (`tools/simulator26.py`) that replicates the 2026 MicroPython environment on your host machine without needing physical hardware.

### Running the Simulator

```bash
# Launch the main menu (default):
make sim

# Launch a specific app:
make sim APP=flappy
make sim APP=plucky_cluck
make sim APP=clock

# Customize window scale (default is 4x):
make sim APP=flappy SCALE=5

# Clear persistent state before running:
python3 tools/badge.py sim flappy --clean

# View live performance/framerate statistics:
python3 tools/badge.py sim flappy --perf
```

### Controls & Keybindings

| Badge Control / Action | Keyboard Keys | Description |
| --- | --- | --- |
| **D-Pad Up** | `Up Arrow` / `W` | Directional Up |
| **D-Pad Down** | `Down Arrow` / `S` | Directional Down |
| **D-Pad Left** | `Left Arrow` / `A` | Directional Left |
| **D-Pad Right** | `Right Arrow` / `D` | Directional Right |
| **Button SELECT** | `Enter` / `Space` / `Z` | Primary action / confirm / jump |
| **Button BACK** | `Escape` / `Backspace` / `X` | Return to previous screen / cancel |
| **Button MENU** | `Tab` / `M` | Open menu / secondary action |
| **Button HOME** | `H` | Return to main menu launcher |
| **Rotate / Flip 180°** | `R` | Toggle badge orientation (upside-down mode) |
| **Screenshot** | `F12` | Save native resolution PNG to `screenshots/` |
| **Quit Simulator** | Close window / `Ctrl+C` | Exit application |

### What the Simulator Replicates
- **2026 Globals**: Provides `badge`, `screen`, `image`, `font`, `color`, `shape`, `brush`, `vec2`, `rect`, `mat3`, and `run()`.
- **Orientation Awareness**: Swapping orientation via `R` flips screen rendering and swaps D-Pad directions (`BUTTON_UP` becomes bottom physical button).
- **Filesystem Virtualization**: Transparently redirects `/system` to local `badge/` and `/state` to `.badge_state/`.
- **Dynamic Resolution**: Supports dynamic switching between `LORES` (160x120) and `HIRES` (320x240).
- **Persistent State**: Simulates `badgeware.State.load()` and `badgeware.State.save()` saving JSON files to `.badge_state/`.
- **Mock Hardware**: Stubs `badge.battery()`, `badge.is_charging()`, `wifi`, `secrets`, and `requests`.

---

## Working with Physical Badge Hardware

Connect the badge via USB-C. The badge presents a USB serial CDC device (`2e8a:1101 Pimoroni Tufty 2350 MicroPython`).

> **Note**: Only one process can access the serial port at any time. Ensure Thonny, `screen`, and other serial clients are closed.

### Common Commands

| Task | Make Command | Direct CLI Command |
| --- | --- | --- |
| **Scan connected devices** | `make devs` | `python3 tools/badge.py devs` |
| **Open interactive REPL** | `make repl` | `python3 tools/badge.py repl` |
| **List badge files** | `make ls` | `python3 tools/badge.py ls :/system/apps` |
| **Soft-reset badge** | `make reset` | `python3 tools/badge.py reset` |
| **Live mount workspace** | `make mount APP=flappy` | `python3 tools/badge.py deploy flappy --mount` |
| **Deploy app to badge** | `make deploy APP=flappy` | `python3 tools/badge.py deploy flappy` |

### Persistent Deployment Note

On production 2026 firmware, `/system` is mounted read-only in the normal REPL:
- **Fast iteration / testing**: Use `make mount APP=...` (`mpremote mount badge`) to execute your host files on the badge directly over serial without copying.
- **Persistent install**: Boot into **USB Mass Storage mode** (double-tap Reset or run the `mass_storage` app from the menu), and copy files directly into the badge's `/system/` volume.

---

## 2026 MicroPython API Quick Reference

### Globals Provided by Runtime
The Universe 2026 firmware provides common utilities in the global scope — do not import `screen`, `image`, or button constants from `badgeware`:

- `badge`: timing, inputs, orientation, IMU, battery, display modes
- `screen`: display surface (`screen.pen`, `screen.clip`, `screen.text()`, `screen.shape()`, `screen.blit()`)
- `color`: `color.rgb(r, g, b)`
- `image`: `image.load(path)`, `.spritesheet(cols, rows)`
- `font`: `font.nope`, `font.sins`, `font.ark`, `font.ziplock`
- `shape`: `shape.rectangle()`, `shape.rounded_rectangle()`
- `run`: frame loop runner `run(update)`

### Orientation-Aware Inputs
Always use logical button constants:
- `BUTTON_UP`, `BUTTON_DOWN`, `BUTTON_LEFT`, `BUTTON_RIGHT`
- `BUTTON_SELECT`, `BUTTON_BACK`, `BUTTON_MENU`, `BUTTON_HOME`

Methods:
```python
if badge.pressed(BUTTON_SELECT):
    ...
if badge.held(BUTTON_LEFT):
    x -= speed * (badge.ticks_delta / 1000)
if badge.released(BUTTON_BACK):
    ...
```

### Frame-Rate Independence
Always multiply speeds and animations by `(badge.ticks_delta / 1000)`:
```python
x += speed_px_per_sec * (badge.ticks_delta / 1000)
```

### Persistent State
Store user data and settings using `badgeware.State`:
```python
from badgeware import State

state = {"highscore": 0}
State.load("my_game", state)

# Save on meaningful milestones:
State.save("my_game", state)
```

---

## VS Code Integration

- **Run Tests / Validate**: `Cmd+Shift+P` -> `Tasks: Run Task` -> `Validate Badge Apps` (or `Cmd+Shift+B` default test task).
- **Badge Commands**: Run tasks to scan devices, open the REPL, or reset the badge.
- **Launch Configurations**: Debug and validate badge apps directly from the VS Code Run & Debug panel.

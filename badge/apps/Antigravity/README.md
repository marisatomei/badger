# Antigravity Companion for Universe Badge

Monitor your Google Antigravity coding sessions on your hardware badge with an animated Anti-G Bot companion.

```text
┌─────────────────────────────────┐                 ┌─────────────────────────────┐
│         LAPTOP / HOST           │                 │     UNIVERSE 2026 BADGE     │
│                                 │                 │                             │
│  • Google Antigravity (IDE/CLI) │   HTTP POST     │  • Animated Mascot (12 fps) │
│  • Lifecycle Hooks (hooks.json) ├────────────────►│  • MicroPython HTTP Server  │
│    OR Transcript Watcher Daemon │   (:80 /state)  │  • Agent & Usage Indicators │
│  • Pairing Client (bridge.py)   │                 │  • Wi-Fi Discovery (UDP)    │
└─────────────────────────────────┘                 └─────────────────────────────┘
```

The badge displays real-time session states (`working`, `attention`, `complete`, `idle`, `sleep`) alongside active agent indicators and token/request usage lines.

---

## Complete Setup Guide: Badge & Laptop Working Together

### Phase 1: Badge Setup

1. **Copy the App to the Badge:**
   - Plug the badge into your laptop via USB in mass-storage mode.
   - Copy the entire folder [`badge/apps/Antigravity`](./) into **`BADGER/apps/Antigravity`** (or `/system/apps/Antigravity` on the device filesystem).
   - Eject the mass-storage drive cleanly.

2. **Configure Wi-Fi on the Badge:**
   - Create a file named **`/antigravity_config.json`** on the root of the badge filesystem (you can also use the existing `/copilot_config.json`):
     ```json
     {
       "ssid": "YOUR_2.4GHZ_WIFI_NAME",
       "password": "YOUR_WIFI_PASSWORD"
     }
     ```
   - *Tip:* You can copy this file via USB mass storage root, or via `mpremote`:
     ```sh
     mpremote fs cp my_wifi.json :/antigravity_config.json
     ```

3. **Launch the App on the Badge:**
   - Restart the badge and select **Antigravity** from the launcher menu.
   - Once connected to your local Wi-Fi network, the badge will display its local IP address (e.g., `192.168.1.150`) and status: `Up: pair Antigravity`.

---

### Phase 2: Pairing Laptop & Badge

Pairing requires physical access to the badge and generates an 8-digit single-use PIN.

1. On the badge, press **Up** to start the 60-second pairing window. An 8-digit code appears on screen (e.g. `48192031`).
2. On your laptop terminal, run:
   ```sh
   python tools/antigravity_bridge/antigravity_bridge.py pair 48192031 --host 192.168.1.150
   ```
   *(Replace `192.168.1.150` with your badge's IP address and `48192031` with the PIN on your badge screen).*
3. **Success!** The bridge exchanges the PIN for an authenticated bearer token and saves it to `~/.gemini/antigravity_badge.json`. The badge screen immediately acknowledges the pairing.

---

### Phase 3: Putting Everything to Work Together

You have two easy ways to drive the badge from Antigravity:

#### Method A: Automatic Background Hooks (Recommended)
This approach automatically triggers the badge during real Antigravity sessions without needing an extra terminal open.

1. Copy or merge [`tools/antigravity_bridge/hooks.json`](../../tools/antigravity_bridge/hooks.json) into your Antigravity customization folder:
   - **For this workspace:** `.agents/hooks.json`
   - **Or globally for all projects:** `~/.gemini/config/hooks.json`
2. Now whenever Antigravity runs (in Antigravity IDE, CLI, or Antigravity 2.0):
   - **Agent starts planning/thinking:** Badge switches to **Working** (mascot eyes focused, energy rings spinning).
   - **Agent runs tools or asks for confirmation:** Badge switches to **Needs attention** (amber alert ring, curious tilted posture).
   - **Agent completes turn:** Badge switches to **Complete!** (emerald green celebratory bounce).
   - **Inactivity:** Badge returns to **Idle** and eventually dozes off to **Sleep**.

#### Method B: Real-Time Transcript Watcher Daemon
If you prefer not to touch `hooks.json`, run the lightweight session watcher:

```sh
python tools/antigravity_bridge/antigravity_bridge.py watch
```

The watcher auto-detects your active Antigravity conversation log (`transcript.jsonl`) and streams every turn and tool call to the badge in real time.

---

### Phase 4: Verification & Manual Testing

Verify your laptop can communicate with the badge at any time:

1. **Check Status:**
   ```sh
   python tools/antigravity_bridge/antigravity_bridge.py status
   ```
   Expected output: `Status (200): {'deviceId': '...', 'boot': ..., 'protocol': 8, 'character': 'antigravity', ...}`

2. **Test States Manually:**
   ```sh
   python tools/antigravity_bridge/antigravity_bridge.py state working
   python tools/antigravity_bridge/antigravity_bridge.py state attention
   python tools/antigravity_bridge/antigravity_bridge.py state complete
   python tools/antigravity_bridge/antigravity_bridge.py state idle
   ```

3. **Test Active Agent Indicators & Usage Lines:**
   ```sh
   python tools/antigravity_bridge/antigravity_bridge.py agents "antigravity=w,linter=a"
   python tools/antigravity_bridge/antigravity_bridge.py usage "Tokens: 14k|Turns: 3"
   ```

---

## Badge Controls

| Button | Action |
| :--- | :--- |
| **Up** | Open 60-second pairing window / Cancel pairing |
| **Down** | Toggle between live session monitoring and offline Demo mode |
| **Left / Right** | Change mascot mood manually (in offline Demo mode only) |
| **Select** | Reload Wi-Fi configuration / Retry network connection |
| **Back** | Exit app and return to badge launcher |

---

## Troubleshooting

- **Badge displays "Wi-Fi unavailable; retrying":** Ensure your Wi-Fi credentials in `/antigravity_config.json` match a 2.4 GHz Wi-Fi network (the RP2350/ESP32 Wi-Fi hardware does not connect to 5 GHz-only bands).
- **Pairing times out:** Make sure your laptop and badge are on the same Wi-Fi network/subnet and that your laptop firewall allows outbound HTTP traffic on port 80.
- **Lost pairing / Re-pairing:** You can re-open the pairing window at any time by pressing **Up** on the badge and re-running the `pair` command. Existing tokens can be overwritten safely.

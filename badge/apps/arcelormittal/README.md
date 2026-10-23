# ArcelorMittal Badge

Display a custom ArcelorMittal branded profile badge with animated logo, GitHub stats, and LinkedIn sharing.

## Usage

- **Left / Right / Up / Down**: Toggle between the ArcelorMittal company card view and your GitHub stats view.
- **Select**: Open the scannable QR code view to share your LinkedIn or GitHub profile (press Left/Right in QR view to switch between LinkedIn and GitHub QR codes).
- **Hold Badges Back-to-Back**: Automatically triggers IR contact card swapping compatible with the Contacts app.
- **Hold Left + Right**: Force refresh your GitHub profile and contribution data over Wi-Fi.
- **Back**: Return to the main menu.

## Installation on Physical Badge

1. Enter **USB Mass Storage** mode on your badge (launch the **Mass Storage** app or double-tap the physical **Reset** button).
2. Copy `badge/apps/arcelormittal` into `system/apps/arcelormittal` on the mounted badge volume.
3. Copy `badge/apps/menu/app.py` into `system/apps/menu/app.py` to enable top menu placement and the animated multi-color ArcelorMittal menu tile.
4. Safely eject the USB drive and press **Reset**.

## Custom Profile Photo & GitHub Account

This app uses `AM_GITHUB_USERNAME` (defaulting to `mgliot`) and dedicated cache files (`/state/am_badge_*`) so it stays completely separate from the main Badge app's `GITHUB_USERNAME`. You can also place a custom 130x130 PNG image at `badge/apps/arcelormittal/assets/profile.png` to override the avatar.

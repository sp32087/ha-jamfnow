# HA Jamf Now Integration

Home Assistant custom integration for Jamf Now device management.

## What It Does
- Authenticates with Jamf Now using your username/password.
- Discovers your Jamf-managed devices and exposes sensors for status, OS version, blueprint, last check-in, lost mode, and supervised state.
- Provides service calls to run Jamf actions (lost mode, restart, shutdown, blueprint assignment, inventory sync).
- Uses the HA device target selector so you pick Jamf devices directly.

## Installation
1) Copy `custom_components/jamfnow` into your HA `custom_components/` folder (or install via HACS using this repo URL).
2) Restart Home Assistant.
3) Add the integration via Settings → Devices & Services → “Add Integration” → Jamf Now, then enter your Jamf Now username/password (and optional base URL).

## Entities
- Sensors per device: `Jamf Now Status`, `OS Version`, `Blueprint`, `Last Check-in`, `Lost Mode Status`, `Supervised`.
- No buttons; all actions are services.

## Services
All services require a Jamf Now device target (use the device picker).

- `jamfnow.enable_lost_mode`
  - `message` (text) — lock screen message (defaults to “Lost mode enabled via Home Assistant”).
  - `phone` (text) — phone number to show.
  - `footnote` (text) — optional footer text.
  - `play_sound` (boolean) — play sound immediately.

- `jamfnow.disable_lost_mode`
  - No extra fields; just target the device.

- `jamfnow.restart_device`
  - No extra fields; just target the device.

- `jamfnow.shutdown_device`
  - No extra fields; just target the device.

- `jamfnow.sync_inventory`
  - No extra fields; triggers an inventory sync.

- `jamfnow.set_blueprint`
  - `blueprint_id` (text) — target blueprint ID to assign.

## Notes
- Lost Mode actions only work on supervised devices (service will error otherwise).
- If you omit `message` in `enable_lost_mode`, the default message is used.
- Update interval defaults to 300 seconds; adjust in code if needed.

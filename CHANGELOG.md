# Changelog

## 0.1.0 (2026-11-16)

First version.

- Reads the Contour xPress Multimedia Controller directly through Windows HID: no driver or extra library needed.
  Reconnects automatically when the device is unplugged and plugged back in.
- Krita AI Diffusion integration: generate, apply, new seed, Live on/off, strength on the ring,
  result history and seed history on the jog wheel.
- Configurable mapping in `%APPDATA%\krita\krita_dial.json`, with per-workspace overrides
  and any Krita action on any button.
- "Krita Dial" docker: device and AI status, last input, on-screen simulator, mapping reload.

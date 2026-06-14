# Zenith Desktop — Install Guide

## Quick install

| Platform | File | Steps |
|----------|------|--------|
| **macOS** | `.dmg` | Open DMG → drag Zenith to Applications → launch |
| **Windows** | `.exe` | Run installer → launch from Start menu |
| **Linux** | `.AppImage` or `.deb` | Make executable (AppImage) or `sudo dpkg -i` (deb) |

Download links: [https://rajverse.me/download](https://rajverse.me/download)

## Unsigned beta warnings

Current releases are **unsigned** (no Apple notarization or Windows Authenticode yet).

### macOS (Gatekeeper)

1. If you see “Zenith cannot be opened because the developer cannot be verified”:
   - Open **System Settings → Privacy & Security**
   - Click **Open Anyway** for Zenith, **or**
   - Right-click the app in Applications → **Open** → confirm

### Windows (SmartScreen)

1. If SmartScreen blocks the installer:
   - Click **More info**
   - Click **Run anyway**

The app then behaves like opening [rajverse.me](https://rajverse.me) in Edge or Chrome.

## System requirements

- **RAM:** 4 GB minimum (8 GB recommended)
- **Network:** Required — the app loads the live website
- **OS:** macOS 11+, Windows 10+ (64-bit), or Ubuntu 20.04+ / equivalent Linux

## Verify downloads

Each GitHub Release includes `SHA256SUMS.txt`. Example:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

Checksums are also shown on `/download` when published by CI.

## Auto-updates

When code signing is enabled (Phase 30+), the desktop shell can check GitHub Releases for newer `desktop-v*.*.*` tags. Until then, revisit `/download` or GitHub Releases to reinstall.

## Development

See [desktop/README.md](../../desktop/README.md) in the repo.

## Code signing (operators)

See [SIGNING.md](./SIGNING.md) when you are ready for Apple Developer ($99/yr) and Windows OV certificates.

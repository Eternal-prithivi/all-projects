# Desktop code signing (future)

Zenith desktop releases are **unsigned** today. This document is the checklist when you are ready to pay for certificates.

## Why sign?

| Platform | Without signing | With signing |
|----------|-----------------|--------------|
| macOS | Gatekeeper warning | Notarized DMG opens normally |
| Windows | SmartScreen “unknown publisher” | Fewer warnings with OV cert |

Linux AppImage/deb generally does not require paid signing.

## macOS (~$99/year)

1. Enroll in [Apple Developer Program](https://developer.apple.com/programs/)
2. Create **Developer ID Application** certificate in Xcode or Apple Developer portal
3. Export as `.p12` for CI
4. GitHub Actions secrets:
   - `APPLE_CERTIFICATE_BASE64` — base64 of `.p12`
   - `APPLE_CERTIFICATE_PASSWORD`
   - `APPLE_ID` — Apple ID email
   - `APPLE_APP_SPECIFIC_PASSWORD` — for notarization
   - `APPLE_TEAM_ID`
5. In `desktop/package.json` → `build.mac`: `hardenedRuntime`, `entitlements`, `notarize` via `electron-builder`

## Windows (~$200–400/year)

1. Purchase an **OV code signing certificate** from a trusted CA (DigiCert, Sectigo, etc.)
2. GitHub Actions secret: `WINDOWS_CERTIFICATE_BASE64` + password
3. In `desktop/package.json` → `build.win`: `certificateFile`, `certificatePassword`

## CI changes

Extend `.github/workflows/desktop-release.yml`:

- Import certs in build jobs before `npm run build`
- Set `CSC_LINK` / `CSC_KEY_PASSWORD` (electron-builder convention)
- Remove `prerelease: true` when stable

## Auto-update

With signed builds, enable `electron-updater` in `desktop/electron/main.js` (already stubbed). Configure `publish` in `package.json`:

```json
"publish": [{ "provider": "github", "owner": "Eternal-prithiviraj", "repo": "all-projects" }]
```

Updates trigger on new `desktop-v*.*.*` GitHub Releases.

## User-facing copy

Update `/download` beta badge and `releases.json` `"beta": false` when signed releases ship.

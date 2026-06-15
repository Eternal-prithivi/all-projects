# Zenith Desktop (Electron)

Native window that loads the live Zenith web app — same experience as Chrome, Edge, or Safari.

## Requirements

- Node.js 20+
- macOS, Windows, or Linux for local development

## Development

```bash
cd desktop
npm install
npm run dev
```

Optional: point at staging or local frontend:

```bash
ZENITH_APP_URL=https://rajverse.me npm run dev
ZENITH_APP_URL=http://localhost:5173 npm run dev
```

## Build installers (unsigned beta)

Icons are generated from `assets/brand/zenith-icon.png` (same Z mark as the web app) via `npm run icons`, which runs automatically before each build.

```bash
npm run icons       # regenerate build/icon.icns, icon.ico, icons/*.png
npm run build:mac    # .dmg in dist/
npm run build:win    # NSIS .exe in dist/
npm run build:linux  # .AppImage + .deb in dist/
```

CI builds run on `desktop-v*.*.*` tags via `.github/workflows/desktop-release.yml`.

## Security notes

- `nodeIntegration` is off; `contextIsolation` is on.
- External links open in the system browser.
- Unsigned builds may show Gatekeeper (macOS) or SmartScreen (Windows) warnings — see `/download` install instructions.
- **Code signing:** see [docs/desktop/SIGNING.md](../docs/desktop/SIGNING.md) when ready for Apple Developer + Windows OV certs.
- **Auto-update:** packaged builds check GitHub Releases via `electron-updater` (best with signed releases).

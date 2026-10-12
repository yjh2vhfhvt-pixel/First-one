# Mensch-Radar

Single-page web app (`index.html`), served via GitHub Pages from branch
`claude/radar-app-person-detection-6xh9fq`. Installed on the user's home screen as a PWA.

## Releasing an update
Every change that is pushed must bump the version, so installed apps reload themselves:
- `APP_VERSION` in `index.html`
- `version.json`
(both must hold the same value). The home-screen icon never needs to be re-added.

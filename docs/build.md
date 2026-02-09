# Building the launcher (Windows)

## Setup

```powershell
py -3.12 -m venv .venv312
.venv312\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## Build with the spec (recommended)

```powershell
Remove-Item -Recurse -Force .\\build, .\\dist -ErrorAction SilentlyContinue
python -m PyInstaller --clean --noconfirm pyinstaller\\realms_launcher.spec
```

Notes:
- Assets are bundled from the repo `assets/` folder.
- The entrypoint is `src/realms_launcher/__main__.py` (spec sets `pathex=['src']`).
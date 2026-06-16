# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for MeteoceanForecast.

Run from the repo root: `pyinstaller MeteoceanForecast.spec`

`launcher.py` is the only analyzed entry point; Home.py and the page scripts
are loaded dynamically by Streamlit at runtime (not imported by launcher.py),
so they are bundled as raw `datas` rather than discovered by static analysis.
Their actual Python dependencies (meteocean_forecast, plotly, ...) are pulled
in because launcher.py imports them directly — see the comment in launcher.py.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

REPO_ROOT = Path(SPECPATH)
STREAMLITAPP_DIR = REPO_ROOT / "streamlitapp"
APP_DIR = STREAMLITAPP_DIR / "app"
SRC_DIR = STREAMLITAPP_DIR / "src"
MODELS_DIR = STREAMLITAPP_DIR / "models"
BUNDLED_CONFIG = REPO_ROOT / ".streamlit" / "config.toml"

block_cipher = None


def _tree_datas(root: Path, dest_root: Path, *, exclude_suffixes: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """Collect (src, dest_dir) pairs for every file under `root`, preserving its
    path relative to the repo root so the bundle layout matches the source layout."""
    datas = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix in exclude_suffixes:
            continue
        dest_dir = dest_root / path.relative_to(root).parent
        datas.append((str(path), str(dest_dir)))
    return datas


datas = []
binaries = []
hiddenimports = []

for package in ("streamlit", "prophet", "cmdstanpy"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

datas += _tree_datas(APP_DIR, Path("streamlitapp") / "app")
# Placed at the bundle root (not "streamlitapp/models") to match
# path_utils.get_models_dir() == <exe_parent>/models, the external/replaceable
# resource path users update post-install without a rebuild.
datas += _tree_datas(MODELS_DIR, Path("models"), exclude_suffixes=(".pkl",))
datas += [(str(BUNDLED_CONFIG), ".streamlit")]

a = Analysis(
    [str(REPO_ROOT / "launcher.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MeteoceanForecast",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MeteoceanForecast",
)

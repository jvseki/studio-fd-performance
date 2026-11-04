# -*- mode: python ; coding: utf-8 -*-
"""Build Windows em pasta: bibliotecas visíveis e sem compressão UPX."""
from importlib.metadata import distribution
from pathlib import Path
import sys

project = Path(SPECPATH).parent
sys.path.insert(0, str(project))

datas = [(str(project / "assets"), "assets")]
datas += [(str(path), str(path.parent.relative_to(project)))
          for path in (project / "migrations").rglob("*.py")]
datas += [(str(project / "docs" / "COMO_USAR.md"), "ajuda")]
datas += [(str(project / "docs" / "ATUALIZACOES.md"), "ajuda")]
datas += [(str(project / "packaging" / "THIRD_PARTY_NOTICES.txt"), "licencas")]
datas += [(str(project / "packaging" / "licenses"), "licencas/Qt-OpenSource")]
for package in ("PySide6", "PySide6_Essentials", "shiboken6", "SQLAlchemy", "alembic", "greenlet", "Mako", "MarkupSafe", "typing_extensions"):
    dist = distribution(package)
    for entry in dist.files or []:
        name = str(entry).lower()
        if "license" in name or "copying" in name:
            source = Path(dist.locate_file(entry))
            if source.is_file():
                datas.append((str(source), str(Path("licencas") / package / Path(str(entry)).parent)))
datas.append((str(Path(sys.base_prefix) / "LICENSE.txt"), "licencas/Python"))

a = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=["sqlalchemy.dialects.sqlite", "alembic.ddl.sqlite"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtQml", "PySide6.QtQuick", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Studio FD Performance",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(project / "assets" / "app.ico"),
    version=str(project / "build" / "windows_version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Studio FD Performance")

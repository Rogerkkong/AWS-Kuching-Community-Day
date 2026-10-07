# PyInstaller one-folder build:  pyinstaller packaging/pyinstaller.spec --noconfirm
# Models are NOT bundled: they live in Ollama or in models/ next to the executable (llamacpp backend).
# The publisher PRIVATE key is never bundled; only app/resources/publisher_public.pem is.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "ui" / "dist"), "ui/dist"),
    (str(ROOT / "app" / "resources" / "publisher_public.pem"), "app/resources"),
    (str(ROOT / "data" / "glossary.json"), "data"),
]
datas += collect_data_files("sqlite_vec")
binaries = collect_dynamic_libs("sqlite_vec")
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("app")
    + ["sqlite_vec", "pymupdf", "multipart", "python_multipart", "webview.platforms.edgechromium", "webview.platforms.winforms"]
)

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "numpy.tests", "PIL.ImageQt", "sentence_transformers", "torch", "pytest", "pytest_socket"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PekelilingNavigator",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PekelilingNavigator")

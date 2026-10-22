"""在 Windows 上构建无需另装 Python 的桌面应用。"""

from pathlib import Path
from importlib import metadata
import shutil
import sys


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("请在 Windows 上构建 Windows 桌面应用。")
    import PyInstaller.__main__

    root = Path(__file__).resolve().parent
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "courseware-kit",
        "--distpath", str(root / "dist"),
        "--workpath", str(root / "build"),
        "--specpath", str(root / "build"),
        "--collect-all", "tkinterdnd2",
        "--collect-all", "pypdfium2",
        str(root / "courseware_gui.pyw"),
    ])
    shutil.copy2(root / "LICENSE", root / "dist" / "LICENSE")
    _copy_licenses(root / "dist" / "licenses")


def _copy_licenses(destination: Path) -> None:
    """将二进制依赖的许可声明和应用一起交付。"""
    for name in ("pypdf", "python-pptx", "pypdfium2", "tkinterdnd2",
                 "Pillow", "lxml", "XlsxWriter", "typing_extensions", "pyinstaller"):
        distribution = metadata.distribution(name)
        for entry in distribution.files or ():
            label = str(entry).lower()
            if "license" not in label and not Path(label).name.startswith(("copying", "notice", "copyright")):
                continue
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                # 元数据偶尔使用 ../，不能让许可文件逃离输出目录。
                relative = Path(*[part for part in entry.parts if part not in ("..", ".")])
                target = destination / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    runtime = Path(sys.base_prefix)
    for source in (runtime / "LICENSE.txt", *list((runtime / "tcl").rglob("license.terms"))):
        if source.is_file():
            target = destination / "python-tcl-tk" / source.relative_to(runtime)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


if __name__ == "__main__":
    main()

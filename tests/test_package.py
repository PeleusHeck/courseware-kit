from importlib import import_module
from pathlib import Path


def test_package_public_api(tmp_path, monkeypatch):
    project = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(project))
    package = import_module("courseware")
    assert package.__version__ == "0.1.0"
    assert set(package.__all__) == {
        "merge_pdfs", "split_pdf", "extract_pdf", "extract_pptx",
    }
    assert all(callable(getattr(package, name)) for name in package.__all__)

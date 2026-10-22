from pathlib import Path
import time
from types import SimpleNamespace

import pytest
from tkinterdnd2 import TkinterDnD

from courseware import desktop, gui


def test_desktop_mixed_files_and_progress(tmp_path, blank_pdf, sample_pptx):
    output = tmp_path / "资料输出" / "复习资料.md"
    events = []
    result = desktop.create_review(
        [blank_pdf, sample_pptx, sample_pptx], output, "考试复习",
        lambda *event: events.append(event),
    )
    assert result.output == output.resolve()
    assert result.files == 2 and result.pages == 1 and result.blocks == 5
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# 考试复习\n")
    assert text.index("## lecture\n") < text.index("## slides\n")
    assert "> 备注：重点复习" in text
    assert events[0][:2] == (0, 2) and events[-1][:2] == (2, 2)


def test_desktop_errors_preserve_existing_output(tmp_path, blank_pdf, sample_pptx, monkeypatch):
    output = tmp_path / "review.md"
    output.write_text("旧的复习资料", encoding="utf-8")
    invalid = tmp_path / "wrong.txt"
    invalid.write_text("text", encoding="utf-8")
    for paths in ([], [invalid], [tmp_path / "missing.pdf"], [blank_pdf]):
        with pytest.raises(ValueError):
            desktop.create_review(paths, output)
        assert output.read_text(encoding="utf-8") == "旧的复习资料"

    def fail_to_save(docs, destination, title):
        Path(destination).write_text("部分内容", encoding="utf-8")
        raise OSError("模拟保存失败")

    monkeypatch.setattr(desktop, "build_review", fail_to_save)
    with pytest.raises(OSError, match="模拟保存失败"):
        desktop.create_review([sample_pptx], output)
    assert output.read_text(encoding="utf-8") == "旧的复习资料"
    assert not list(tmp_path.glob(".courseware-*.md"))


def test_gui_file_selection_generates_markdown(tmp_path, sample_pptx, monkeypatch):
    root = TkinterDnD.Tk()
    root.withdraw()
    app = gui.ReviewApp(root)
    output = tmp_path / "generated.md"
    errors = []
    monkeypatch.setattr(gui.filedialog, "askopenfilenames", lambda **kw: (str(sample_pptx),))
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda **kw: str(output))
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *a, **kw: errors.append(a))
    try:
        assert root.tk.call("package", "present", "tkdnd")
        app.choose_button.invoke()
        assert app.busy
        deadline = time.monotonic() + 15
        while app.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(0.01)
        assert not app.busy and not errors
        assert output.is_file() and app.result.output == output.resolve()
        assert "已生成" in app.status.get()
        assert "## slides" in app.preview.get("1.0", "end")
        assert str(app.open_button["state"]) == "normal"
    finally:
        root.destroy()


def test_gui_drop_paths_and_save_cancel(tmp_path, sample_pptx, monkeypatch):
    root = TkinterDnD.Tk()
    root.withdraw()
    app = gui.ReviewApp(root)
    copy = tmp_path / "课件 有空格.pptx"
    copy.write_bytes(sample_pptx.read_bytes())
    selected = []
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda **kw: "")
    try:
        app.start_files([copy])
        assert not app.busy and app.result is None
        monkeypatch.setattr(app, "start_files", lambda paths: selected.extend(paths))
        data = root.tk.call("format", "%s", root.tk.call("list", str(copy), str(sample_pptx)))
        assert app.drop_files(SimpleNamespace(data=data)) == "copy"
        assert selected == [str(copy), str(sample_pptx)]
        app.busy = True
        assert app.drop_files(SimpleNamespace(data=data)) == "none"
        assert len(selected) == 2
    finally:
        root.destroy()

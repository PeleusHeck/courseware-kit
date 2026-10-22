import json

import pytest

from courseware.cli import main


def test_cli_pipeline_and_exit_codes(tmp_path, blank_pdf, sample_pptx, capsys):
    output = tmp_path / "all"
    assert main(["all", "-o", str(output), str(blank_pdf), str(sample_pptx)]) == 0
    docs = json.loads((output / "docs.json").read_text(encoding="utf-8"))
    assert [doc["source"] for doc in docs] == ["lecture.pdf", "slides.pptx"]
    assert [doc["type"] for doc in docs] == ["pdf", "pptx"]
    review = (output / "review.md").read_text(encoding="utf-8")
    assert "## lecture\n" in review
    assert "## slides\n" in review
    assert "> 备注：重点复习" in review
    assert capsys.readouterr().err == ""

    with pytest.raises(SystemExit) as exc:
        main(["split", "-o", str(output), str(blank_pdf), "--every", "0"])
    assert exc.value.code == 2
    assert capsys.readouterr().err

    assert main(["extract", "-o", str(output / "bad.json"),
                 str(tmp_path / "missing.pdf")]) == 1
    captured = capsys.readouterr()
    assert "missing.pdf" in captured.err
    assert "Traceback" not in captured.err
    assert not captured.out

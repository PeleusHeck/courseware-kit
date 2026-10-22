from pathlib import Path

import pytest
from pypdf import PdfReader

from courseware.pdf_ops import merge_pdfs, split_pdf


def test_merge_and_split_blank_pdf(tmp_path, blank_pdf):
    merged = tmp_path / "merged" / "combined.pdf"
    assert merge_pdfs([str(blank_pdf), str(blank_pdf)], str(merged)) is None
    reader = PdfReader(str(merged))
    assert [int(page.mediabox.width) for page in reader.pages] == [200, 201, 202] * 2
    assert [item.title for item in reader.outline] == ["lecture", "lecture"]
    assert [reader.get_destination_page_number(item) for item in reader.outline] == [0, 3]

    cases = [
        ("range", "1-2,3", [2, 1]),
        ("every", 2, [2, 1]),
        ("bookmark", None, [2, 1]),
    ]
    for mode, value, expected in cases:
        paths = split_pdf(str(blank_pdf), mode, str(tmp_path / mode), value)
        assert all(Path(path).is_file() for path in paths)
        assert [len(PdfReader(path).pages) for path in paths] == expected

    merge_pdfs([str(blank_pdf)], str(merged), add_bookmarks=False)
    assert not PdfReader(str(merged)).outline
    with pytest.raises(ValueError, match="missing.pdf"):
        merge_pdfs([str(tmp_path / "missing.pdf")], str(merged))

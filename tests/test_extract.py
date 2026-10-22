from courseware.extract import extract_pdf, extract_pptx


def test_extract_blank_pdf_structure(tmp_path, blank_pdf):
    assert blank_pdf.parent == tmp_path
    result = extract_pdf(str(blank_pdf))
    assert set(result) == {"source", "type", "pages"}
    assert result == {"source": "lecture.pdf", "type": "pdf", "pages": []}


def test_extract_pptx_structure(tmp_path, sample_pptx):
    assert sample_pptx.parent == tmp_path
    result = extract_pptx(str(sample_pptx))
    assert result == {
        "source": "slides.pptx",
        "type": "pptx",
        "pages": [{
            "index": 1,
            "blocks": [
                {"level": 0, "text": "标题"},
                {"level": 2, "text": "要点"},
                {"level": 0, "text": "组合文本"},
                {"level": 0, "text": "A | B"},
                {"level": 0, "text": "备注：重点复习"},
            ],
        }],
    }

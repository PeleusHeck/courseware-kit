from copy import deepcopy

from courseware.organize import build_review, merge_blocks


def test_build_review_and_merge_blocks(tmp_path):
    docs = [{
        "source": "lecture01.pdf",
        "type": "pdf",
        "pages": [
            {"index": 1, "blocks": [
                {"level": 0, "text": "知识点"},
                {"level": 0, "text": "知识点"},
                {"level": 0, "text": "补充说明"},
                {"level": 0, "text": "备注：重点复习"},
            ]},
            {"index": 2, "title": "总结", "blocks": [
                {"level": 0, "text": "**保留 Markdown**"},
            ]},
        ],
    }]
    original = deepcopy(docs)
    output = tmp_path / "nested" / "review.md"
    assert build_review(docs, str(output)) is None
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# 复习资料\n")
    assert "**目录**" in text
    assert "- [lecture01](#lecture01)" in text
    assert "## lecture01\n" in text
    assert "### 第 1 页\n" in text
    assert "### 总结\n" in text
    assert "- 知识点；补充说明\n" in text
    assert text.count("知识点") == 1
    assert "> 备注：重点复习\n" in text
    assert "- **保留 Markdown**\n" in text
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert merge_blocks({"pages": [
        {"blocks": [{"level": 0, "text": "A"}, {"level": 0, "text": "B"}]},
        {"blocks": [{"level": 0, "text": "C"}]},
    ]}) == [{"level": 0, "text": "A；B"}, {"level": 0, "text": "C"}]
    assert docs == original

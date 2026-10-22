"""将课件提取结果整理成带目录的 Markdown 复习资料。"""

from pathlib import Path
import re


def _flush_blocks(result: list[dict], pending: list[str]) -> None:
    if pending:
        result.append({"level": 0, "text": "".join(pending)})
        pending.clear()


def merge_blocks(doc: dict, max_chars: int = 60) -> list[dict]:
    """返回按页序展开的 block 列表；只在同一页内合并，不修改输入。

    每个原始短块分别判断长度；合并结果可以超过 max_chars。
    备注不参与合并，以便在输出中保留独立的引用格式。
    """
    result = []
    for page in doc["pages"]:
        pending = []
        for block in page["blocks"]:
            text = block["text"]
            if not text:
                continue
            if (block["level"] == 0 and len(text) < max_chars
                    and not text.startswith("备注：")):
                if pending:
                    pending.append("；")
                pending.append(text)
            else:
                _flush_blocks(result, pending)
                result.append(dict(block))
        _flush_blocks(result, pending)
    return result


def _deduplicate_pages(doc: dict) -> list[dict]:
    """在每份课件内连续去重，跨页保留比较状态，保留原始页信息。"""
    pages = []
    previous = None
    for page in doc["pages"]:
        blocks = []
        for block in page["blocks"]:
            text = block["text"]
            if not text:
                continue
            if text != previous:
                blocks.append(dict(block))
            previous = text
        copied = dict(page)
        copied["blocks"] = blocks
        pages.append(copied)
    return pages


def _anchor(text: str, used: set[str]) -> str:
    """生成保留中文的锚点，并为重复标题添加数字后缀。"""
    base = re.sub(r"[^\w\s-]", "", text.lower())
    base = re.sub(r"\s", "-", base)
    candidate = base
    suffix = 1
    while candidate in used:
        pieces = []
        pieces.append(base)
        pieces.append("-")
        pieces.append(str(suffix))
        candidate = "".join(pieces)
        suffix = suffix + 1
    used.add(candidate)
    return candidate


def _heading(
    parts: list[str], toc: list[str], used: set[str], text: str, level: int
) -> None:
    anchor = _anchor(text, used)
    parts.append("#" * level)
    parts.append(" ")
    parts.append(text)
    parts.append("\n\n")
    if level == 2:
        toc.append("- [")
        toc.append(text)
        toc.append("](#")
        toc.append(anchor)
        toc.append(")\n")


def _render_block(
    parts: list[str], toc: list[str], used: set[str], block: dict
) -> None:
    text = block["text"]
    if text.startswith("备注："):
        for line in text.splitlines():
            parts.append("> ")
            parts.append(line)
            parts.append("\n")
        parts.append("\n")
    elif block["level"] in (1, 2, 3):
        _heading(parts, toc, used, text, block["level"])
    else:
        parts.append("- ")
        parts.append(text)
        parts.append("\n\n")


def build_review(
    docs: list[dict], out_md: str, title: str = "复习资料"
) -> None:
    """按输入顺序输出 Markdown，目录包含所有二级标题。"""
    parts, toc, heading = [], [], []
    used = set()
    _heading(heading, toc, used, title, 1)
    for doc in docs:
        _heading(parts, toc, used, Path(doc["source"]).stem, 2)
        for page in _deduplicate_pages(doc):
            page_title = page.get("title")
            if not page_title:
                label = []
                label.append("第 ")
                label.append(str(page["index"]))
                label.append(" 页")
                page_title = "".join(label)
            _heading(parts, toc, used, page_title, 3)
            for block in merge_blocks({"pages": [page]}):
                _render_block(parts, toc, used, block)
    output = []
    output.append("".join(heading))
    output.append("**目录**\n\n")
    output.append("".join(toc))
    output.append("\n")
    output.append("".join(parts))
    text = "".join(output).rstrip("\n")
    final = []
    final.append(text)
    final.append("\n")
    destination = Path(out_md)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(final), encoding="utf-8", newline="\n")

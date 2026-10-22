"""桌面端复用的课件处理流程，不依赖图形界面。"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from .extract import extract_pdf, extract_pptx
from .organize import build_review


@dataclass(frozen=True)
class ReviewResult:
    output: Path
    files: int
    pages: int
    blocks: int


def create_review(
    paths: Sequence[str | Path],
    out_md: str | Path,
    title: str = "复习资料",
    progress: Callable[[int, int, str], None] | None = None,
) -> ReviewResult:
    """按选择顺序提取课件，成功后原子替换目标文件，失败保留旧文件。"""
    sources = _validate_sources(paths)
    output = Path(out_md).expanduser().resolve()
    if output.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("请将复习资料保存为 .md 或 .markdown 文件。")
    if output in sources:
        raise ValueError("保存位置不能覆盖原始课件。")
    docs = []
    extractors = {".pdf": extract_pdf, ".pptx": extract_pptx}
    for index, source in enumerate(sources):
        if progress:
            progress(index, len(sources), f"正在读取：{source.name}")
        docs.append(extractors[source.suffix.lower()](str(source)))
    pages = sum(len(doc["pages"]) for doc in docs)
    blocks = sum(len(page["blocks"]) for doc in docs for page in doc["pages"])
    if not any(block["text"].strip() for doc in docs for page in doc["pages"]
               for block in page["blocks"]):
        raise ValueError("课件中未找到可提取的文字。纯图片或扫描件暂不支持 OCR。")
    if progress:
        progress(len(sources), len(sources), "正在生成复习资料…")
    _save_review(docs, output, title.strip() or "复习资料")
    return ReviewResult(output, len(sources), pages, blocks)


def _validate_sources(paths: Sequence[str | Path]) -> list[Path]:
    if not paths:
        raise ValueError("请先选择至少一份 PDF 或 PPTX 课件。")
    sources, seen = [], set()
    for item in paths:
        path = Path(item).expanduser().resolve()
        if path.suffix.lower() not in {".pdf", ".pptx"}:
            raise ValueError(f"不支持的文件：{path.name}。请选择 PDF 或 PPTX。")
        if not path.is_file():
            raise ValueError(f"找不到课件文件：{path.name}")
        key = os.path.normcase(str(path))
        if key not in seen:
            sources.append(path)
            seen.add(key)
    return sources


def _save_review(docs: list[dict], output: Path, title: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=output.parent, prefix=".courseware-", suffix=".md", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        build_review(docs, str(temporary), title)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)

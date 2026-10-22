"""使用 pypdf 合并 PDF，或按页码范围、固定页数和顶层书签拆分。"""

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError


def _read_pdf(path: str) -> PdfReader:
    """读取到内存，并将文件读取、PDF 解析错误转换为包含文件名的异常。"""
    source = Path(path)
    try:
        reader = PdfReader(BytesIO(source.read_bytes()))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("PDF 需要密码")
        len(reader.pages)
        return reader
    except (OSError, PyPdfError, ValueError) as exc:
        raise ValueError(f"无法读取 PDF {source.name!r}: {exc}") from exc


def _parse_ranges(s: str) -> list[tuple[int, int]]:
    """解析从 1 开始、两端均包含的范围，保留段的顺序和重复项。"""
    if not isinstance(s, str) or not s.strip():
        raise ValueError("页码范围必须是非空字符串，例如 '1-5,8,10-12'")
    ranges = []
    for part in s.split(","):
        match = re.fullmatch(r"([0-9]+)(?:\s*-\s*([0-9]+))?", part.strip())
        if match is None:
            raise ValueError(f"无效的页码范围: {part!r}")
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        if start < 1 or end < start:
            raise ValueError(f"页码必须从 1 开始且范围不能倒序: {part!r}")
        ranges.append((start, end))
    return ranges


def _bookmark_ranges(reader: PdfReader) -> list[tuple[int, int]]:
    """仅使用顶层书签；按页码去重排序，并保留书签前的页面。"""
    starts = set()
    for item in reader.outline:
        if isinstance(item, list):
            continue
        page = reader.get_destination_page_number(item)
        if page is None or not 0 <= page < len(reader.pages):
            raise ValueError("顶层书签包含无效的页面目标")
        starts.add(page + 1)
    if not starts:
        raise ValueError("PDF 没有顶层书签")
    boundaries = sorted(starts | {1}) + [len(reader.pages) + 1]
    return [(start, stop - 1) for start, stop in zip(boundaries, boundaries[1:])]


def _split_ranges(
    reader: PdfReader, mode: str, value: str | int | None
) -> list[tuple[int, int]]:
    """在生成任何文件之前验证拆分参数和全部页码。"""
    page_count = len(reader.pages)
    if page_count == 0:
        raise ValueError("PDF 没有可拆分的页面")
    if mode == "range":
        if not isinstance(value, str):
            raise ValueError("range 模式的 value 必须是页码范围字符串")
        ranges = _parse_ranges(value)
    elif mode == "every":
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("every 模式的 value 必须是正整数")
        ranges = [
            (start, min(start + value - 1, page_count))
            for start in range(1, page_count + 1, value)
        ]
    elif mode == "bookmark":
        ranges = _bookmark_ranges(reader)
    else:
        raise ValueError(f"不支持的拆分模式: {mode!r}")
    if any(end > page_count for _, end in ranges):
        raise ValueError(f"页码范围超出 PDF 总页数 {page_count}")
    return ranges


def merge_pdfs(
    paths: list[str], out_path: str, add_bookmarks: bool = True
) -> None:
    """按输入顺序合并；可为每个非空输入文件添加一个文件名书签。"""
    if not paths:
        raise ValueError("paths 不能为空")
    with PdfWriter() as writer:
        for path in paths:
            reader = _read_pdf(path)
            if not reader.pages:
                continue
            try:
                writer.append(
                    reader,
                    outline_item=Path(path).stem if add_bookmarks else None,
                    import_outline=False,
                )
            except (PyPdfError, ValueError) as exc:
                raise ValueError(f"无法合并 PDF {Path(path).name!r}: {exc}") from exc
        output = Path(out_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        writer.write(str(output))


def split_pdf(
    path: str, mode: str, out_dir: str, value: str | int | None = None
) -> list[str]:
    """拆分为 <原文件名>_<序号>_<起始页>-<结束页>.pdf，返回写入路径。"""
    reader = _read_pdf(path)
    ranges = _split_ranges(reader, mode, value)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, (start, end) in enumerate(ranges, start=1):
        output = directory / f"{Path(path).stem}_{index:03d}_{start}-{end}.pdf"
        with PdfWriter() as writer:
            writer.append(reader, pages=(start - 1, end), import_outline=False)
            writer.write(str(output))
        outputs.append(str(output))
    return outputs

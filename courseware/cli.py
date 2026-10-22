"""课件整理器命令行入口；仅负责参数、文件格式转换和函数调度。"""

import argparse
from importlib import import_module
import json
from pathlib import Path
import sys


def _module(name: str):
    """同时支持 python cli.py 和 python -m 包名.cli，并延迟加载依赖。"""
    if __package__:
        return import_module(f".{name}", __package__)
    return import_module(name)


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def _page_range(value: str) -> str:
    try:
        _module("pdf_ops")._parse_ranges(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def _course_file(value: str) -> str:
    if Path(value).suffix.lower() not in {".pdf", ".pptx"}:
        raise argparse.ArgumentTypeError(f"仅支持 PDF 和 PPTX 文件：{value}")
    return value


def _extract_docs(paths: list[str]) -> list[dict]:
    module = _module("extract")
    extractors = {".pdf": module.extract_pdf, ".pptx": module.extract_pptx}
    return [extractors[Path(path).suffix.lower()](path) for path in paths]


def _write_json(docs: list[dict], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(docs, ensure_ascii=False, indent=2)
    output.write_text(f"{content}\n", encoding="utf-8", newline="\n")


def _merge(args: argparse.Namespace) -> None:
    _module("pdf_ops").merge_pdfs(
        args.files, args.output, add_bookmarks=not args.no_bookmarks
    )


def _split(args: argparse.Namespace) -> None:
    mode, value = "bookmark", None
    if args.page_range is not None:
        mode, value = "range", args.page_range
    elif args.every is not None:
        mode, value = "every", args.every
    _module("pdf_ops").split_pdf(args.file, mode, args.output, value)


def _extract(args: argparse.Namespace) -> None:
    _write_json(_extract_docs(args.files), args.output)


def _organize(args: argparse.Namespace) -> None:
    docs = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    if not isinstance(docs, list) or any(not isinstance(doc, dict) for doc in docs):
        raise ValueError("输入 JSON 必须是课件文档对象组成的数组")
    _module("organize").build_review(docs, args.output, title=args.title)


def _all(args: argparse.Namespace) -> None:
    directory = Path(args.output)
    docs = _extract_docs(args.files)
    _write_json(docs, directory / "docs.json")
    _module("organize").build_review(docs, str(directory / "review.md"))


def _add_merge(subparsers) -> None:
    parser = subparsers.add_parser(
        "merge", help="按顺序合并 PDF", description="按输入顺序合并 PDF，可关闭文件名书签。"
    )
    parser.add_argument("-o", dest="output", required=True, metavar="OUT", help="输出 PDF")
    parser.add_argument("files", nargs="+", metavar="FILE", help="按顺序排列的 PDF")
    parser.add_argument("--no-bookmarks", action="store_true", help="不添加文件名书签")
    parser.set_defaults(handler=_merge)


def _add_split(subparsers) -> None:
    parser = subparsers.add_parser(
        "split", help="拆分 PDF", description="按页码范围、固定页数或顶层书签拆分 PDF。"
    )
    parser.add_argument("-o", dest="output", required=True, metavar="OUT_DIR", help="输出目录")
    parser.add_argument("file", metavar="FILE", help="输入 PDF")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--range", dest="page_range", type=_page_range, metavar="R", help="例如 1-5,8,10-12")
    modes.add_argument("--every", type=_positive_int, metavar="N", help="每 N 页一个文件")
    modes.add_argument("--bookmark", action="store_true", help="按顶层书签拆分")
    parser.set_defaults(handler=_split)


def _add_extract(subparsers) -> None:
    parser = subparsers.add_parser(
        "extract", help="提取 PDF/PPTX 文本", description="按输入顺序提取混合的 PDF、PPTX，输出 JSON 数组。"
    )
    parser.add_argument("-o", dest="output", required=True, metavar="OUT_JSON", help="输出 JSON")
    parser.add_argument("files", nargs="+", type=_course_file, metavar="FILE", help="PDF 或 PPTX")
    parser.set_defaults(handler=_extract)


def _add_organize(subparsers) -> None:
    parser = subparsers.add_parser(
        "organize", help="生成 Markdown 复习资料", description="读取提取结果的 JSON 数组，生成带目录的 Markdown。"
    )
    parser.add_argument("-i", dest="input", required=True, metavar="IN_JSON", help="输入 JSON")
    parser.add_argument("-o", dest="output", required=True, metavar="OUT_MD", help="输出 Markdown")
    parser.add_argument("--title", default="复习资料", metavar="T", help="文档标题（默认：复习资料）")
    parser.set_defaults(handler=_organize)


def _add_all(subparsers) -> None:
    parser = subparsers.add_parser(
        "all", help="提取并生成复习资料", description="依次执行提取和整理，在输出目录生成 docs.json 与 review.md。"
    )
    parser.add_argument("-o", dest="output", required=True, metavar="OUT_DIR", help="输出目录")
    parser.add_argument("files", nargs="+", type=_course_file, metavar="FILE", help="PDF 或 PPTX")
    parser.set_defaults(handler=_all)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="课件整理器：合并、拆分、提取和整理课件。")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    for add_command in (_add_merge, _add_split, _add_extract, _add_organize, _add_all):
        add_command(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        args.handler(args)
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""课件整理器的公共提取与 PDF 操作接口。"""

from .pdf_ops import merge_pdfs, split_pdf
from .extract import extract_pdf, extract_pptx

__version__ = "0.2.0"

__all__ = ["merge_pdfs", "split_pdf", "extract_pdf", "extract_pptx"]

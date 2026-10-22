"""本地课件整理窗口：选择或拖入文件后，选择保存位置并自动生成。"""

import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from . import __version__
from .desktop import ReviewResult, create_review


class ReviewApp:
    def __init__(self, root: tk.Tk, *, drag_enabled: bool = True):
        self.root = root
        self.busy = False
        self.result: ReviewResult | None = None
        self.events = Queue()
        self._poll_id = None
        root.title("课件整理器 · courseware-kit")
        root.geometry("860x700")
        root.minsize(740, 600)
        root.configure(bg="#f3f6fb")
        root.protocol("WM_DELETE_WINDOW", self._close)
        self.title = tk.StringVar(root, "复习资料")
        self.status = tk.StringVar(root, "准备好了，选择课件即可开始。")
        self.saved_path = tk.StringVar(root, "生成后会在这里显示保存位置")
        self._build_ui(drag_enabled)

    def _build_ui(self, drag_enabled: bool) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 11), padding=12)
        style.configure("TProgressbar", background="#2563eb")
        body = tk.Frame(self.root, bg="#f3f6fb", padx=30, pady=24)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="课件整理器", font=("Microsoft YaHei UI", 23, "bold"),
                 bg="#f3f6fb", fg="#17243c").pack(anchor="w")
        tk.Label(body, text="把 PDF / PPTX 变成一份复习资料 · 本地处理，无需上传",
                 font=("Microsoft YaHei UI", 10), bg="#f3f6fb", fg="#64748b").pack(anchor="w", pady=(4, 18))
        self._build_drop_area(body, drag_enabled)
        self._build_options(body)
        self._build_preview(body)
        self.progress = ttk.Progressbar(body, maximum=100)
        self.progress.pack(fill="x", pady=(16, 8))
        tk.Label(body, textvariable=self.status, bg="#f3f6fb", fg="#334155",
                 font=("Microsoft YaHei UI", 10), anchor="w", wraplength=770).pack(fill="x")
        self._build_footer(body)

    def _build_drop_area(self, parent, enabled: bool) -> None:
        frame = tk.Frame(parent, bg="white", highlightthickness=2, highlightbackground="#c4d4ef", pady=18)
        frame.pack(fill="x")
        caption = "将 PDF / PPTX 拖到这里" if enabled else "选择一份或多份 PDF / PPTX"
        label = tk.Label(frame, text=caption, font=("Microsoft YaHei UI", 14, "bold"), bg="white", fg="#1e3a5f")
        label.pack()
        detail = tk.Label(frame, text="可以混合选择多个课件，选择保存位置后自动生成",
                          font=("Microsoft YaHei UI", 10), bg="white", fg="#64748b")
        detail.pack(pady=(5, 12))
        self.choose_button = ttk.Button(frame, text="选择课件并生成复习资料", style="Primary.TButton", command=self.choose_files)
        self.choose_button.pack()
        if enabled:
            for widget in (frame, label, detail, self.choose_button):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.drop_files)
        self.files_label = tk.Label(parent, text="支持 .pdf、.pptx · 无需预先合并或转换格式",
                                    bg="#f3f6fb", fg="#64748b", anchor="w", wraplength=770)
        self.files_label.pack(fill="x", pady=(8, 14))

    def _build_options(self, parent) -> None:
        row = tk.Frame(parent, bg="#f3f6fb")
        row.pack(fill="x", pady=(0, 14))
        tk.Label(row, text="资料标题", bg="#f3f6fb", fg="#334155").pack(side="left", padx=(0, 12))
        self.title_entry = ttk.Entry(row, textvariable=self.title)
        self.title_entry.pack(side="left", fill="x", expand=True)

    def _build_preview(self, parent) -> None:
        tk.Label(parent, text="生成预览", font=("Microsoft YaHei UI", 11, "bold"),
                 bg="#f3f6fb", fg="#17243c").pack(anchor="w", pady=(0, 7))
        frame = tk.Frame(parent, bg="white")
        frame.pack(fill="both", expand=True)
        self.preview = tk.Text(frame, height=9, wrap="word", relief="flat", padx=14, pady=12,
                               font=("Microsoft YaHei UI", 10), bg="white", fg="#334155")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.preview.pack(side="left", fill="both", expand=True)
        self._set_preview("复习资料会包含课件目录、逐页内容和 PPTX 备注。\n\n选择课件后，先确认 Markdown 保存位置，随后自动开始生成。\n纯图片或扫描件暂不支持 OCR。")

    def _build_footer(self, parent) -> None:
        tk.Label(parent, textvariable=self.saved_path, bg="#f3f6fb", fg="#64748b",
                 anchor="w", wraplength=770).pack(fill="x", pady=(8, 10))
        row = tk.Frame(parent, bg="#f3f6fb")
        row.pack(fill="x")
        self.open_button = ttk.Button(row, text="打开 Markdown", state="disabled", command=self.open_result)
        self.open_button.pack(side="left")
        self.folder_button = ttk.Button(row, text="打开保存目录", state="disabled", command=self.open_folder)
        self.folder_button.pack(side="left", padx=8)
        tk.Label(row, text=f"v{__version__}", bg="#f3f6fb", fg="#94a3b8").pack(side="right")

    def _set_preview(self, text: str) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def choose_files(self) -> None:
        if self.busy:
            return
        paths = filedialog.askopenfilenames(
            parent=self.root, title="选择课件（可多选 PDF 和 PPTX）",
            filetypes=[("PDF / PPTX 课件", "*.pdf *.pptx *.PDF *.PPTX")],
        )
        if paths:
            self.start_files(paths)

    def drop_files(self, event) -> str:
        if self.busy:
            return "none"
        paths = self.root.tk.splitlist(event.data)
        if paths:
            self.start_files(paths)
        return "copy"

    def start_files(self, paths) -> None:
        if self.busy:
            return
        from .desktop import _validate_sources
        try:
            sources = _validate_sources(paths)
        except (ValueError, OSError) as exc:
            messagebox.showerror("无法添加课件", str(exc), parent=self.root)
            return
        destination = filedialog.asksaveasfilename(
            parent=self.root, title="保存复习资料", defaultextension=".md",
            initialdir=str(sources[0].parent), initialfile="复习资料.md",
            filetypes=[("Markdown 学习资料", "*.md")], confirmoverwrite=True,
        )
        if not destination:
            return
        self.result = None
        self.busy = True
        self.progress["value"] = 0
        self.status.set("正在准备课件…")
        self.saved_path.set(destination)
        self.files_label.configure(text="已选择：" + "、".join(path.name for path in sources))
        self._set_preview("正在提取课件，请稍候…")
        for button in (self.choose_button, self.open_button, self.folder_button, self.title_entry):
            button.configure(state="disabled")
        Thread(target=self._worker, args=(sources, destination, self.title.get()), daemon=True).start()
        self._poll_id = self.root.after(80, self._poll)

    def _worker(self, sources, destination: str, title: str) -> None:
        try:
            result = create_review(sources, destination, title, lambda done, total, text:
                                   self.events.put(("progress", (done, total, text))))
            self.events.put(("done", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _poll(self) -> None:
        self._poll_id = None
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    done, total, text = value
                    self.progress["value"] = 100 * done / total
                    self.status.set(text)
                else:
                    self._finish(value if kind == "done" else None,
                                 value if kind == "error" else None)
        except Empty:
            pass
        if self.busy:
            self._poll_id = self.root.after(80, self._poll)

    def _finish(self, result: ReviewResult | None, error: str | None) -> None:
        self.busy = False
        self.choose_button.configure(state="normal")
        self.title_entry.configure(state="normal")
        if error is not None:
            self.progress["value"] = 0
            self.status.set("生成失败，请检查课件后重新选择。")
            self._set_preview(error)
            messagebox.showerror("生成失败", error, parent=self.root)
            return
        self.result = result
        self.progress["value"] = 100
        self.saved_path.set(str(result.output))
        self.status.set(f"已生成 · {result.files} 份课件 · {result.pages} 页 · 保存为 Markdown")
        self.open_button.configure(state="normal")
        self.folder_button.configure(state="normal")
        try:
            with result.output.open(encoding="utf-8") as handle:
                self._set_preview(handle.read(16000))
        except OSError:
            self._set_preview("资料已保存，请点击“打开保存目录”查看。")

    def open_result(self) -> None:
        if self.result:
            self._open(self.result.output)

    def open_folder(self) -> None:
        if self.result:
            self._open(self.result.output.parent)

    def _open(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("无法打开", f"文件已保存在：{path}\n{exc}", parent=self.root)

    def _close(self) -> None:
        if self.busy:
            messagebox.showinfo("正在生成", "正在处理课件，请生成完成后再关闭窗口。", parent=self.root)
            return
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
        self.root.destroy()


def main() -> None:
    try:
        root = TkinterDnD.Tk()
        drag_enabled = True
    except tk.TclError:
        root = tk.Tk()
        drag_enabled = False
    ReviewApp(root, drag_enabled=drag_enabled)
    root.mainloop()


if __name__ == "__main__":
    main()

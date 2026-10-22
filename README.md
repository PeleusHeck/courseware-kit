# courseware-kit：课件整理器

一个将 PDF、PPTX 课件整理成 Markdown 复习资料的桌面应用，同时保留合并、拆分和命令行功能。

## 桌面版：选择课件即可生成

1. 启动应用，将一份或多份 PDF / PPTX 拖入窗口，也可以点击“选择课件并生成复习资料”。
2. 选择 Markdown 保存位置，确认后自动开始生成。
3. 完成后可在窗口预览，点击“打开 Markdown”或“打开保存目录”查看完整资料。

课件只在本机处理，不上传服务器。标题可以修改，多个文件按照传入顺序整理；重复选择同一个文件只处理一次。纯图片或扫描件暂不支持 OCR。

Windows 64 位用户可以双击构建好的 `courseware-kit.exe` 使用，无需安装 Python。推送代码后，GitHub 的 Actions → Test and build Windows app → 成功的运行记录 → Artifacts 中可下载 `courseware-kit-windows`，解压后运行。

## 功能

- 合并：按文件顺序合并 PDF，可添加文件名书签。
- 拆分：按页码范围、固定页数或顶层书签拆分 PDF。
- 提取：混合处理 PDF 和 PPTX，输出统一的 JSON；支持 PPTX 表格、组合形状和备注，不做 OCR，跳过无文本页面。
- 整理：生成带目录的 Markdown，连续去重、合并同页短正文，并保留备注。

## 安装

需要 Python 3.11+，在项目目录执行：

```shell
pip install -r requirements.txt
pip install -e .
```

启动图形界面：

```shell
courseware-gui
```

也可以运行 `python -m courseware.gui`；Windows 安装依赖后可双击项目根目录的 `courseware_gui.pyw`。使用 Python 运行图形界面需要 Tcl/Tk（Windows 官方 Python 安装程序自带；Ubuntu/Debian 可安装 `python3-tk`）。如系统不支持原生拖拽，可通过按钮选择文件。

## 示例命令

将示例中的文件名替换为自己的课件路径，在项目目录运行：

```shell
courseware merge -o output/merged.pdf lecture01.pdf lecture02.pdf
courseware split -o output/parts output/merged.pdf --every 5
courseware extract -o output/docs.json lecture01.pdf lecture02.pptx
courseware organize -i output/docs.json -o output/review.md --title "复习资料"
courseware all -o output/all lecture01.pdf lecture02.pptx
```

`all` 依次执行提取和整理，生成 `docs.json` 和 `review.md`。页码从 1 开始；命令成功返回 0，参数错误返回 2，运行时错误输出到 stderr 并返回 1。

未安装命令入口时，也可以用 `python -m courseware.cli` 替代 `courseware`。

## 输出示例

以下展示一份 `review.md` 的前 15 行，空行计入行数：

```markdown
# 复习资料

**目录**

- [lecture01](#lecture01)

## lecture01

### 第 1 页

# 知识要点

- 概念 A；概念 B

> 备注：重点复习
```

## 测试

```shell
python -m pytest tests -q
```

测试使用 `tmp_path` 现场生成课件；PDF 测试数据由 pypdf 生成，为 3 页空白 PDF，不测试 PDF 文本提取精度。还验证图形窗口、多选文件、拖拽路径、后台生成、取消保存及失败时保留原文件。图形测试需要桌面环境，Linux 无显示环境可使用 `xvfb-run -a python -m pytest -q`。

## 构建 Windows 应用

在 Windows 上执行：

```shell
pip install ".[build]"
python build_windows.py
```

输出为 `dist/courseware-kit.exe`，双击即可运行。

## 许可证

本项目使用 [MIT 许可证](LICENSE)。

PDF 文本提取依赖 pypdfium2，已移除 PyMuPDF。pypdfium2 使用 Apache-2.0 / BSD-3-Clause 许可；分发包含 PDFium 的二进制包时，需要随附 PDFium 及其依赖的许可证，详见 [官方许可说明](https://github.com/pypdfium2-team/pypdfium2#licensing)。

桌面拖拽依赖 tkinterdnd2；其随附 TkDND 的许可证随依赖分发。Windows 构建使用 PyInstaller，其许可证包含允许分发生成应用的例外。

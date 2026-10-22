# courseware-kit：课件整理器

一个将 PDF、PPTX 课件合并、拆分、提取文字并整理成 Markdown 复习资料的 Python 命令行工具。

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

共 6 个用例，使用 `tmp_path` 现场生成课件；PDF 测试数据由 pypdf 生成，为 3 页空白 PDF，不测试 PDF 文本提取精度。

## 许可证

本项目使用 [MIT 许可证](LICENSE)。

PDF 文本提取依赖 pypdfium2，已移除 PyMuPDF。pypdfium2 使用 Apache-2.0 / BSD-3-Clause 许可；分发包含 PDFium 的二进制包时，需要随附 PDFium 及其依赖的许可证，详见 [官方许可说明](https://github.com/pypdfium2-team/pypdfium2#licensing)。

import os
import json
import shutil
import argparse

from pathlib import Path
from pdf_craft.llm import LLM
from pdf_craft import OCRLevel, PDFPageExtractor, ExtractedTableFormat,generate_epub_file, TableRender, LaTeXRender
from pdf_craft.analysers import analyse


def main() -> None:
  parser = argparse.ArgumentParser(description="PDF 分析和转换工具")
  parser.add_argument("--file", required=True, help="要处理的 PDF 文件路径")
  args = parser.parse_args()

  llm=LLM(
    **_read_format_json(),
    #log_dir_path=_project_dir_path("analysing") / "log",
  )
  extractor=PDFPageExtractor(
    device="cuda",
    ocr_level=OCRLevel.OncePerLayout,
    extract_formula=True, # 开启公式识别
    extract_table_format=ExtractedTableFormat.HTML, # 开启表格识别（以 MarkDown 格式保存）
    model_dir_path=str(_project_dir_path("models")),
    debug_dir_path=str(_project_dir_path("analysing") / "plot"),
  )
  analyse(
    llm=llm,
    pdf_page_extractor=extractor,
    correction=True,
    pdf_path=Path(args.file),
    analysing_dir_path=_project_dir_path("analysing",clean=True),
    output_path=_project_dir_path("output", clean=True),
  )
  generate_epub_file(
    from_dir_path=_project_dir_path("output"), # 来自上一步分析所产生的文件夹
    epub_file_path=_project_dir_path("output") / "epub", # 生成的 EPUB 文件保存路径
    table_render=TableRender.HTML, # 表格渲染模式
    latex_render=LaTeXRender.SVG, # 公式渲染模式
  )

def _read_format_json() -> dict:
  path = os.path.join(__file__, "..", "format.json")
  path = os.path.abspath(path)
  with open(path, mode="r", encoding="utf-8") as file:
    return json.load(file)

def _project_dir_path(name: str, clean: bool = False) -> Path:
  path = Path(__file__) / ".." / name
  path = path.resolve()
  if clean:
    shutil.rmtree(path, ignore_errors=True)
  path.mkdir(parents=True, exist_ok=True)
  return path

if __name__ == "__main__":
  main()
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
  parser.add_argument("--translate", action="store_true", help="启用中文翻译功能")
  parser.add_argument("--target-lang", default="zh-CN", help="目标翻译语言（默认：zh-CN）")
  parser.add_argument("--translation-mode", choices=["replace", "dual", "separate"],
                     default="replace", help="翻译模式：replace(单语替换，默认), dual(双语), separate(分离)")
  parser.add_argument("--restore", action="store_true", help="恢复之前的处理进度，不清理现有文件")
  args = parser.parse_args()

  # 读取配置并根据命令行参数调整
  config = _read_format_json()
  if args.translate:
    config["translation"]["enabled"] = True
    config["translation"]["target_language"] = args.target_lang
    config["translation"]["mode"] = args.translation_mode
    mode_desc = {
      "replace": "单语替换",
      "dual": "双语对照",
      "separate": "分离输出"
    }
    print(f"✓ 翻译功能已启用 - 目标语言: {args.target_lang}, 模式: {mode_desc.get(args.translation_mode, args.translation_mode)}")

  # 恢复模式提示
  if args.restore:
    print("🔄 恢复模式已启用 - 将从之前的进度继续处理")
    print("   - 不会清理现有的 output 和 analysing 文件夹")
    print("   - 将跳过已完成的处理步骤")

    # 检查现有进度
    _check_existing_progress()

  # 如果启用翻译，需要传递翻译配置给分析器
  translation_config = config.get("translation") if args.translate else None

  # 创建 LLM 实例
  llm_config = {k: v for k, v in config.items() if k != "translation"}
  llm = LLM(**llm_config)

  extractor=PDFPageExtractor(
    device="cuda",
    ocr_level=OCRLevel.OncePerLayout,
    extract_formula=True, # 开启公式识别
    extract_table_format=ExtractedTableFormat.HTML, # 开启表格识别（以 HTML 格式保存）
    model_dir_path=str(_project_dir_path("models")),
    debug_dir_path=str(_project_dir_path("analysing") / "plot"),
  )

  # 根据是否恢复模式决定是否清理文件夹
  clean_folders = not args.restore

  # 分析PDF，传递翻译配置
  analyse(
    llm=llm,
    pdf_page_extractor=extractor,
    correction=True,
    pdf_path=Path(args.file),
    analysing_dir_path=_project_dir_path("analysing", clean=clean_folders),
    output_path=_project_dir_path("output", clean=clean_folders),
    translation_config=translation_config,  # 传递翻译配置
  )

  # 生成EPUB文件
  if args.translate:
    if args.translation_mode == "replace":
      epub_filename = f"translated_{args.target_lang}.epub"
    elif args.translation_mode == "dual":
      epub_filename = "bilingual.epub"
    else:  # separate
      epub_filename = "output.epub"
  else:
    epub_filename = "output.epub"

  # 检查是否已存在EPUB文件（恢复模式下）
  epub_path = _project_dir_path("output") / epub_filename
  if args.restore and epub_path.exists():
    print(f"📚 发现已存在的EPUB文件: {epub_filename}")
    user_input = input("是否重新生成EPUB文件？(y/N): ").strip().lower()
    if user_input not in ['y', 'yes']:
      print(f"✓ 跳过EPUB生成，使用现有文件: {epub_filename}")
      return

  generate_epub_file(
    from_dir_path=_project_dir_path("output"), # 来自上一步分析所产生的文件夹
    epub_file_path=epub_path, # 生成的 EPUB 文件保存路径
    table_render=TableRender.HTML, # 表格渲染模式
    latex_render=LaTeXRender.SVG, # 公式渲染模式
  )

  if args.translate:
    print(f"✓ 翻译完成！EPUB文件已生成: {epub_filename}")
  else:
    print(f"✓ 处理完成！EPUB文件已生成: {epub_filename}")

def _check_existing_progress():
  """检查现有的处理进度"""
  base_path = Path(__file__).parent
  analysing_path = base_path / "analysing"
  output_path = base_path / "output"

  print("📊 检查现有进度:")

  # 检查 analysing 文件夹中的各个阶段
  stages = [
    ("ocr", "OCR识别"),
    ("sequence", "序列提取"),
    ("correction", "内容校正"),
    ("contents", "目录提取"),
    ("chapter", "章节生成"),
    ("reference", "引用处理")
  ]

  for stage_dir, stage_name in stages:
    stage_path = analysing_path / stage_dir
    if stage_path.exists() and any(stage_path.iterdir()):
      print(f"   ✅ {stage_name}: 发现已处理的文件")
    else:
      print(f"   ⏸️  {stage_name}: 未开始或未完成")

  # 检查 output 文件夹
  if output_path.exists() and any(output_path.iterdir()):
    print(f"   ✅ 输出文件: 发现已生成的文件")
    # 列出现有的输出文件
    for file in output_path.iterdir():
      if file.is_file():
        print(f"      - {file.name}")
  else:
    print(f"   ⏸️  输出文件: 未生成")

def _read_format_json() -> dict:
  path = os.path.join(__file__, "..", "format.json")
  path = os.path.abspath(path)
  with open(path, mode="r", encoding="utf-8") as file:
    return json.load(file)

def _project_dir_path(name: str, clean: bool = False) -> Path:
  path = Path(__file__) / ".." / name
  path = path.resolve()
  if clean:
    if path.exists():
      print(f"🗑️  清理文件夹: {name}")
      shutil.rmtree(path, ignore_errors=True)
  path.mkdir(parents=True, exist_ok=True)
  return path

if __name__ == "__main__":
  main()
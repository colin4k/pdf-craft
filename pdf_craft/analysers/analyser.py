from os import PathLike
from pathlib import Path
from typing import Optional, Dict, Any

from ..llm import LLM
from ..pdf import PDFPageExtractor

from .ocr import generate_ocr_pages
from .sequence import extract_sequences
from .correction import correct
from .contents import extract_contents
from .chapter import generate_chapters
from .reference import generate_chapters_with_footnotes
from .output import output


def analyse(
    llm: LLM,
    pdf_page_extractor: PDFPageExtractor,
    pdf_path: PathLike,
    analysing_dir_path: PathLike,
    output_path: PathLike,
    correction: bool = False,
    translation_config: Optional[Dict[str, Any]] = None,
  ) -> None:

  max_data_tokens = 4096
  analysing_dir_path = Path(analysing_dir_path)
  ocr_path = analysing_dir_path / "ocr"
  assets_path = analysing_dir_path / "assets"
  sequence_path = analysing_dir_path / "sequence"
  correction_path = analysing_dir_path / "correction"
  contents_path = analysing_dir_path / "contents"
  chapter_path = analysing_dir_path / "chapter"
  reference_path = analysing_dir_path / "reference"

  # 显示翻译模式信息（如果启用）
  if translation_config and translation_config.get("enabled"):
    mode_desc = {
      "replace": "单语替换",
      "dual": "双语对照",
      "separate": "分离输出"
    }
    mode = translation_config.get("mode", "replace")
    print(f"✓ 翻译模式已激活 - 目标语言: {translation_config.get('target_language', 'zh-CN')}, 模式: {mode_desc.get(mode, mode)}")
    print("📝 注意：翻译将在章节生成阶段进行，以确保格式兼容性")

  generate_ocr_pages(
    extractor=pdf_page_extractor,
    pdf_path=Path(pdf_path),
    ocr_path=ocr_path,
    assets_path=assets_path,
  )
  extract_sequences(
    llm=llm,
    workspace=sequence_path,
    ocr_path=ocr_path,
    max_data_tokens=max_data_tokens,
  )
  sequence_output_path = sequence_path / "output"

  if correction:
    sequence_output_path = correct(
      llm=llm,
      workspace=correction_path,
      text_path=sequence_output_path / "text",
      footnote_path=sequence_output_path / "footnote",
      max_data_tokens=max_data_tokens,
    )

  contents = extract_contents(
    llm=llm,
    workspace=contents_path,
    sequence_path=sequence_output_path / "text",
    max_data_tokens=max_data_tokens,
  )

  # 只在章节生成阶段启用翻译包装器
  chapter_llm = llm
  if translation_config and translation_config.get("enabled"):
    chapter_llm = _create_translation_llm_wrapper(llm, translation_config)
    print("🔄 在章节生成阶段启用翻译功能...")

  chapter_output_path, contents = generate_chapters(
    llm=chapter_llm,
    contents=contents,
    sequence_path=sequence_output_path / "text",
    workspace_path=chapter_path,
    max_request_tokens=max_data_tokens,
  )
  footnote_sequence_path = sequence_output_path / "footnote"

  if footnote_sequence_path.exists():
    chapter_output_path = generate_chapters_with_footnotes(
      chapter_path=chapter_output_path,
      footnote_sequence_path=footnote_sequence_path,
      workspace_path=reference_path,
    )

  output(
    contents=contents,
    output_path=Path(output_path),
    chapter_output_path=chapter_output_path,
    assets_path=assets_path,
  )


class _TranslationLLMWrapper:
  """LLM 包装器，在原有功能基础上添加翻译功能"""

  def __init__(self, original_llm: LLM, translation_config: Dict[str, Any]):
    self.original_llm = original_llm
    self.translation_config = translation_config
    self.target_language = translation_config.get("target_language", "zh-CN")
    self.mode = translation_config.get("mode", "replace")

  def __getattr__(self, name):
    """代理所有其他方法到原始 LLM"""
    return getattr(self.original_llm, name)

  def request(self, input_data, parser):
    """重写 request 方法，添加翻译功能"""
    # 检查是否需要翻译（基于输入内容判断）
    if self._should_translate(input_data):
      # 修改输入，添加翻译指令
      modified_input = self._add_translation_instruction(input_data)
      # 调用原始 LLM
      result = self.original_llm.request(modified_input, parser)
      # 处理翻译结果
      return self._process_translation_result(result)
    else:
      # 不需要翻译的内容直接调用原始 LLM
      return self.original_llm.request(input_data, parser)

  def _should_translate(self, input_data) -> bool:
    """判断是否需要翻译此输入"""
    # 更保守的翻译策略：只翻译明显的文本内容
    input_str = str(input_data)
    # 检查是否包含大量文本内容，且不是 XML 或结构化数据
    has_text_content = len(input_str) > 200
    has_translation_keywords = any(keyword in input_str.lower() for keyword in
                                  ['paragraph', 'chapter', 'content', 'text'])
    is_not_xml = '<' not in input_str[:100]  # 简单检查是否为 XML

    return has_text_content and has_translation_keywords and is_not_xml

  def _add_translation_instruction(self, input_data):
    """为输入添加翻译指令"""
    if hasattr(input_data, '__iter__') and not isinstance(input_data, str):
      # 如果是消息列表，修改最后一个用户消息
      modified_input = list(input_data)
      if modified_input and hasattr(modified_input[-1], 'content'):
        original_content = modified_input[-1].content

        # 根据翻译模式生成不同的指令
        if self.mode == "replace":
          translation_instruction = f"""
请完成原有任务，并将所有文本内容翻译为{self.target_language}。

重要：请直接返回翻译后的结果，不要包含原文。保持相同的结构和格式。

原始请求：
{original_content}
"""
        elif self.mode == "dual":
          translation_instruction = f"""
请完成原有任务，并将所有文本内容翻译为{self.target_language}。

请按以下格式返回结果：

## 原始分析结果
{{原有的分析结果}}

## {self.target_language}翻译
{{翻译后的内容，保持相同的结构和格式}}

原始请求：
{original_content}
"""
        else:  # separate mode
          translation_instruction = f"""
请完成原有任务，同时生成{self.target_language}翻译版本。

请分别返回原文和翻译版本，保持相同的结构和格式。

原始请求：
{original_content}
"""

        modified_input[-1].content = translation_instruction
        return modified_input

    return input_data

  def _process_translation_result(self, result):
    """处理包含翻译的结果"""
    # 这里可以根据需要处理翻译结果
    # 目前简单返回原结果，让下游处理
    return result


def _create_translation_llm_wrapper(llm: LLM, translation_config: Dict[str, Any]) -> LLM:
  """创建支持翻译的 LLM 包装器"""
  return _TranslationLLMWrapper(llm, translation_config)

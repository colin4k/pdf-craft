import json
import datetime

from os import PathLike
from pathlib import Path
from typing import cast, Any, Generator
from importlib.resources import files
from jinja2 import Environment, Template
from xml.etree.ElementTree import Element
from pydantic import SecretStr
from logging import getLogger, DEBUG, Formatter, Logger, FileHandler
from tiktoken import get_encoding, Encoding
from langchain_core.messages import SystemMessage, HumanMessage

from ..template import create_env
from ..xml import decode_friendly, encode_friendly
from .increasable import Increasable
from .executor import LLMExecutor


class LLM:
  def __init__(
      self,
      key: str,
      url: str,
      model: str,
      token_encoding: str,
      timeout: float | None = None,
      top_p: float | tuple[float, float] | None = None,
      temperature: float | tuple[float, float] | None = None,
      retry_times: int = 5,
      retry_interval_seconds: float = 6.0,
      log_dir_path: PathLike | None = None,
    ):
    prompts_path = files("pdf_craft").joinpath("data/prompts")
    self._templates: dict[str, Template] = {}
    self._encoding: Encoding = get_encoding(token_encoding)
    self._env: Environment = create_env(prompts_path)
    self._logger_save_path: Path | None = None

    if log_dir_path is not None:
      self._logger_save_path = Path(log_dir_path)
      if not self._logger_save_path.exists():
        self._logger_save_path.mkdir(parents=True, exist_ok=True)
      elif not self._logger_save_path.is_dir():
        self._logger_save_path = None

    self._executor = LLMExecutor(
      url=url,
      model=model,
      api_key=cast(SecretStr, key),
      timeout=timeout,
      top_p=Increasable(top_p),
      temperature=Increasable(temperature),
      retry_times=retry_times,
      retry_interval_seconds=retry_interval_seconds,
      create_logger=self._create_logger,
    )

  def _create_logger(self) -> Logger | None:
    if self._logger_save_path is None:
      return None

    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.strftime("%Y-%m-%d %H-%M-%S %f")
    file_path = self._logger_save_path / f"request {timestamp}.log"
    logger = getLogger(f"LLM Request {timestamp}")
    logger.setLevel(DEBUG)
    handler = FileHandler(file_path, encoding="utf-8")
    handler.setLevel(DEBUG)
    handler.setFormatter(Formatter("%(asctime)s    %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)

    return logger

  def request_markdown(self, template_name: str, user_data: Element | str, params: dict[str, Any] | None = None) -> str:
    if params is None:
      params = {}
    return self._executor.request(
      input=self._create_input(template_name, user_data, params),
      parser=self._encode_markdown,
    )

  def request_json(self, template_name: str, user_data: Element | str, params: dict[str, Any] | None = None) -> Any:
    if params is None:
      params = {}
    return self._executor.request(
      input=self._create_input(template_name, user_data, params),
      parser=self._encode_json,
    )

  def request_xml(self, template_name: str, user_data: Element | str, params: dict[str, Any] | None = None) -> Element:
    if params is None:
      params = {}
    return self._executor.request(
      input=self._create_input(template_name, user_data, params),
      parser=self._encode_xml,
    )

  def _create_input(self, template_name: str, user_data: Element | str, params: dict[str, Any]):
    data: str
    if isinstance(user_data, Element):
      data = encode_friendly(user_data)
      data = f"```XML\n{data}\n```"
    else:
      data = user_data

    template = self._template(template_name)
    prompt = template.render(**params)
    return [
      SystemMessage(content=prompt),
      HumanMessage(content=data)
    ]

  def prompt_tokens_count(self, template_name: str, params: dict[str, Any]) -> int:
    template = self._template(template_name)
    prompt = template.render(**params)
    return len(self._encoding.encode(prompt))

  def encode_tokens(self, text: str) -> list[int]:
    return self._encoding.encode(text)

  def decode_tokens(self, tokens: list[int]) -> str:
    return self._encoding.decode(tokens)

  def count_tokens_count(self, text: str) -> int:
    return len(self._encoding.encode(text))

  def _template(self, template_name: str) -> Template:
    template = self._templates.get(template_name, None)
    if template is None:
      template = self._env.get_template(template_name)
      self._templates[template_name] = template
    return template

  def _encode_markdown(self, response: str) -> str:
    for quote in self._search_quotes("Markdown", response):
      return quote
    raise ValueError("No valid Markdown response found")

  def _encode_json(self, response: str) -> Any:
    for quote in self._search_quotes("JSON", response):
      return json.loads(quote)
    raise ValueError("No valid Markdown response found")

  def _encode_xml(self, response: str) -> Element:
    # 添加调试信息
    print(f"🔍 尝试解析 XML 响应，响应长度: {len(response)} 字符")

    # 尝试从 decode_friendly 获取元素
    elements = list(decode_friendly(response, "response"))
    if elements:
      print(f"✅ 成功解析到 {len(elements)} 个 XML 元素")
      return elements[0]

    # 如果没有找到 "response" 标签，尝试查找其他可能的根元素
    print("🔍 未找到 'response' 标签，尝试查找其他根元素...")

    # 尝试常见的根元素标签
    common_tags = ["correction", "overview", "updation", "request", "result", "output"]
    for tag in common_tags:
      elements = list(decode_friendly(response, tag))
      if elements:
        print(f"✅ 找到 '{tag}' 标签，包含 {len(elements)} 个元素")
        return elements[0]

    # 尝试解析所有可能的 XML 元素
    print("🔍 尝试解析所有 XML 元素...")
    all_elements = list(decode_friendly(response))
    if all_elements:
      print(f"✅ 找到 {len(all_elements)} 个 XML 元素，使用第一个")
      return all_elements[0]

    # 如果仍然失败，显示响应的前500个字符用于调试
    print(f"❌ XML 解析完全失败")
    print(f"📝 响应内容预览（前500字符）:")
    print(response[:500])
    print("..." if len(response) > 500 else "")

    raise ValueError("No valid XML response found")

  def _search_quotes(self, kind: str, response: str) -> Generator[str, None, None]:
    start_marker = f"```{kind}"
    end_marker = "```"
    start_index = 0

    while True:
      start_index = response.find(start_marker, start_index)
      if start_index == -1:
        break
      end_index = response.find(end_marker, start_index + len(start_marker))
      if end_index == -1:
        break
      extracted_text = response[start_index + len(start_marker):end_index].strip()
      yield extracted_text
      start_index = end_index + len(end_marker)
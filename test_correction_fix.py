#!/usr/bin/env python3
"""
测试校正阶段修复的脚本
"""

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement
from pdf_craft.llm import LLM
from pdf_craft.analysers.correction.repeater import _Repeater
from pdf_craft.analysers.utils import Context
from pdf_craft.analysers.correction.common import State


def create_test_request():
    """创建一个测试用的请求元素"""
    request = Element("request")

    # 添加一个测试文本段落
    text = SubElement(request, "text")
    text.set("id", "25/2")

    line1 = SubElement(text, "line")
    line1.set("id", "1")
    line1.text = "This is a test paragraph with some OCR errors."

    line2 = SubElement(text, "line")
    line2.set("id", "2")
    line2.text = "It contains intentional mistakes for testing."

    return request


def create_mock_llm_response():
    """创建一个模拟的LLM响应，只包含overview（表示没有错误）"""
    response = Element("response")

    overview = SubElement(response, "overview")
    overview.set("quality", "perfect")
    overview.set("remain", "false")

    return response


class MockLLM:
    """模拟的LLM类，用于测试"""

    def request_xml(self, template_name, user_data, params):
        print(f"🔍 模拟LLM调用: template={template_name}")
        return create_mock_llm_response()


class MockContext:
    """模拟的Context类"""

    def __init__(self):
        self.state = {"max_data_tokens": 4096}

    def write_xml_file(self, file_path, xml):
        """模拟写入XML文件"""
        print(f"📝 写入文件: {file_path}")
        # 这里可以实际写入文件进行验证
        from pdf_craft.xml import encode_friendly
        content = encode_friendly(xml)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 文件内容长度: {len(content)} 字符")


def test_correction_fix():
    """测试校正修复"""
    print("🧪 开始测试校正阶段修复...")

    # 创建测试目录
    test_dir = Path("test_correction_output")
    test_dir.mkdir(exist_ok=True)

    # 创建模拟对象
    mock_llm = MockLLM()
    mock_context = MockContext()

    # 创建测试请求
    test_request = create_test_request()

    # 创建Repeater实例
    repeater = _Repeater(
        llm=mock_llm,
        context=mock_context,
        save_path=test_dir,
        is_footnote=False
    )

    try:
        # 执行测试
        result = repeater.do(test_request)

        # 检查结果
        print("✅ 测试执行成功")

        # 检查生成的文件
        step_file = test_dir / "step_1.xml"
        if step_file.exists():
            print(f"✅ 步骤文件已生成: {step_file}")

            # 读取并验证文件内容
            with open(step_file, 'r', encoding='utf-8') as f:
                content = f.read()

            print(f"📄 文件内容预览:")
            print(content[:500])

            # 检查是否包含必要的元素
            if "<correction>" in content:
                print("✅ 包含correction根元素")
            if "<overview" in content:
                print("✅ 包含overview元素")
            if "<request>" in content:
                print("✅ 包含request元素")
            else:
                print("❌ 缺少request元素 - 这是之前的问题！")

        else:
            print("❌ 步骤文件未生成")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理测试文件
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("🧹 清理测试文件")


if __name__ == "__main__":
    test_correction_fix()
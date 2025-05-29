#!/usr/bin/env python3
"""
XML 解析测试脚本
用于验证校正阶段的 XML 解析修复是否有效
"""

import sys
from pathlib import Path

# 添加项目路径到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from pdf_craft.xml import decode_friendly

def test_xml_parsing():
    """测试 XML 解析功能"""
    print("🧪 测试 XML 解析功能...")

    # 测试用例1：标准的 response 标签
    test_case_1 = """
    <response>
        <overview quality="good"/>
        <updation>
            <text id="1/1">
                <line id="1">测试内容</line>
            </text>
        </updation>
    </response>
    """

    # 测试用例2：correction 标签（校正阶段常见）
    test_case_2 = """
    <correction>
        <overview quality="fair"/>
        <updation>
            <text id="1/1">
                <line id="1">校正内容</line>
            </text>
        </updation>
    </correction>
    """

    # 测试用例3：没有根标签的内容
    test_case_3 = """
    <overview quality="poor"/>
    <updation>
        <text id="1/1">
            <line id="1">无根标签内容</line>
        </text>
    </updation>
    """

    test_cases = [
        ("标准 response 标签", test_case_1),
        ("correction 标签", test_case_2),
        ("无根标签", test_case_3),
    ]

    for name, xml_content in test_cases:
        print(f"\n📋 测试用例: {name}")
        try:
            # 测试 decode_friendly 函数
            elements = list(decode_friendly(xml_content))
            if elements:
                print(f"✅ 成功解析，找到 {len(elements)} 个元素")
                print(f"   第一个元素标签: {elements[0].tag}")
            else:
                print("❌ 解析失败，未找到任何元素")
        except Exception as e:
            print(f"❌ 解析异常: {e}")

    print("\n🎯 测试完成")

if __name__ == "__main__":
    test_xml_parsing()
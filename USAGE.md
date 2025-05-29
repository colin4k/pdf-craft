# PDF-Craft 使用说明

## 概述

PDF-Craft 是一个强大的 PDF 分析和转换工具，支持 OCR 识别、内容提取、翻译和 EPUB 生成。

## 基本用法

```bash
python pdfcraft.py --file <PDF文件路径> [选项]
```

## 命令行参数

### 必需参数

- `--file <路径>`: 要处理的 PDF 文件路径

### 可选参数

#### 翻译功能
- `--translate`: 启用翻译功能
- `--target-lang <语言>`: 目标翻译语言（默认：zh-CN）
- `--translation-mode <模式>`: 翻译模式
  - `replace`: 单语替换（默认）- 只输出翻译结果
  - `dual`: 双语对照 - 同时显示原文和翻译
  - `separate`: 分离输出 - 生成独立的翻译文件

#### 恢复功能
- `--restore`: 恢复之前的处理进度，不清理现有文件

## 使用示例

### 1. 基本 PDF 处理
```bash
python pdfcraft.py --file document.pdf
```
- 执行完整的 PDF 分析流程
- 生成 `output.epub` 文件

### 2. 启用翻译（单语模式）
```bash
python pdfcraft.py --file document.pdf --translate
```
- 分析 PDF 并翻译为中文
- 只输出翻译后的内容
- 生成 `translated_zh-CN.epub` 文件

### 3. 翻译为其他语言
```bash
python pdfcraft.py --file document.pdf --translate --target-lang en
```
- 翻译为英文
- 生成 `translated_en.epub` 文件

### 4. 双语对照模式
```bash
python pdfcraft.py --file document.pdf --translate --translation-mode dual
```
- 同时保留原文和翻译
- 生成 `bilingual.epub` 文件

### 5. 恢复处理进度
```bash
python pdfcraft.py --file document.pdf --restore
```
- 从之前中断的地方继续处理
- 不会清理现有的 `analysing` 和 `output` 文件夹
- 跳过已完成的处理步骤

### 6. 恢复并启用翻译
```bash
python pdfcraft.py --file document.pdf --translate --restore
```
- 恢复之前的进度并启用翻译功能

## 处理流程

### 标准流程
1. **OCR 识别**: 提取 PDF 中的文本和图像
2. **序列提取**: 分析文本结构和布局
3. **内容校正**: 使用 LLM 校正 OCR 错误
4. **目录提取**: 识别章节结构
5. **章节生成**: 生成结构化内容
6. **引用处理**: 处理脚注和引用
7. **EPUB 生成**: 生成最终的 EPUB 文件

### 恢复模式流程
- 检查现有进度
- 跳过已完成的步骤
- 从中断点继续处理

## 文件结构

```
pdf-craft/
├── analysing/          # 分析过程中的中间文件
│   ├── ocr/           # OCR 识别结果
│   ├── sequence/      # 序列提取结果
│   ├── correction/    # 校正结果
│   ├── contents/      # 目录提取结果
│   ├── chapter/       # 章节生成结果
│   └── reference/     # 引用处理结果
├── output/            # 最终输出文件
├── models/            # AI 模型文件
└── *.epub            # 生成的 EPUB 文件
```

## 翻译功能详解

### 翻译模式对比

| 模式 | 输出内容 | 文件名 | 适用场景 |
|------|----------|--------|----------|
| `replace` | 仅翻译结果 | `translated_{语言}.epub` | 只需要翻译版本 |
| `dual` | 原文+翻译 | `bilingual.epub` | 需要对照阅读 |
| `separate` | 分离文件 | `output.epub` | 需要独立的文件 |

### 支持的语言
- `zh-CN`: 简体中文（默认）
- `en`: 英文
- 其他语言代码（根据 LLM 支持情况）

## 恢复功能详解

### 何时使用恢复功能
- 处理过程中意外中断
- 想要修改某些参数重新处理
- 系统资源不足需要分批处理

### 恢复功能特点
- **智能检测**: 自动检测已完成的处理步骤
- **进度显示**: 显示当前处理进度
- **文件保护**: 不会删除现有的中间文件和输出文件
- **用户确认**: 在覆盖现有 EPUB 文件前会询问用户

### 恢复模式输出示例
```
🔄 恢复模式已启用 - 将从之前的进度继续处理
   - 不会清理现有的 output 和 analysing 文件夹
   - 将跳过已完成的处理步骤

📊 检查现有进度:
   ✅ OCR识别: 发现已处理的文件
   ✅ 序列提取: 发现已处理的文件
   ⏸️  内容校正: 未开始或未完成
   ⏸️  目录提取: 未开始或未完成
   ⏸️  章节生成: 未开始或未完成
   ⏸️  引用处理: 未开始或未完成
   ⏸️  输出文件: 未生成
```

## 配置文件

`format.json` 包含 LLM 和翻译的配置：

```json
{
  "key": "your-api-key",
  "url": "https://api.example.com",
  "model": "model-name",
  "token_encoding": "o200k_base",
  "translation": {
    "enabled": true,
    "target_language": "zh-CN",
    "mode": "replace",
    "prompt_template": "翻译提示模板"
  }
}
```

## 注意事项

1. **GPU 支持**: 默认使用 CUDA 加速，确保有可用的 GPU
2. **模型文件**: 首次运行会下载必要的 AI 模型
3. **网络连接**: 翻译功能需要连接到 LLM 服务
4. **磁盘空间**: 确保有足够的磁盘空间存储中间文件
5. **处理时间**: 大文件处理可能需要较长时间

## 故障排除

### 常见问题

1. **CUDA 错误**: 如果没有 GPU，将 `device="cuda"` 改为 `device="cpu"`
2. **网络超时**: 检查 LLM 服务的网络连接
3. **内存不足**: 使用恢复功能分批处理大文件
4. **模型下载失败**: 检查网络连接和模型路径

### 日志文件
- 处理日志保存在 `analysing/log/` 目录
- 错误信息会显示在控制台

## 性能优化建议

1. **使用 GPU**: 启用 CUDA 加速可显著提升处理速度
2. **恢复功能**: 对于大文件，可以分阶段处理
3. **批量处理**: 一次处理多个相似的 PDF 文件
4. **清理缓存**: 定期清理 `analysing` 文件夹释放磁盘空间
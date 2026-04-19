# GalgameDialogueTranslator

<p align="center">
  <a href="#中文说明"><img alt="中文" src="https://img.shields.io/badge/语言-中文-blue?style=for-the-badge"></a>
  <a href="#english-readme"><img alt="English" src="https://img.shields.io/badge/Language-English-green?style=for-the-badge"></a>
</p>

> **项目标记：本项目完全使用 AI 生成。**
>
> **AI generated project notice: This project was generated entirely with AI assistance.**

## 中文说明

GalgameDialogueTranslator 是一个面向 Windows 的视觉小说 / Galgame 对话翻译悬浮窗工具。

它会截取游戏窗口中的字幕区域，使用 OCR 识别文字，再调用翻译后端，把译文显示在一个置顶窗口中。它不会修改游戏文件，不会注入游戏进程，也不会 patch 内存。

### 快速开始

普通用户建议直接使用 Release 里的打包版本，不需要从源码运行。

1. 从 GitHub Release 下载 `GalgameDialogueTranslator.exe`。
2. 如果 OCR 无法工作，请安装 [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki)。
3. 双击运行 `GalgameDialogueTranslator.exe`。
4. 将游戏设置为窗口化或无边框窗口模式。
5. 在程序中设置：
   - `Window title`：填写游戏窗口标题的一部分。
   - `OCR`：选择 `auto` 或 `tesseract`。
   - `Translator`：选择 `deepseek`、`grok`、`argos` 或 `libretranslate`。
   - 点击 `Place beside game`。
   - 点击 `Start`。

如果识别区域不准确，请调整窗口底部的字幕区域裁剪比例。

### 翻译后端

#### DeepSeek

适合需要较高在线翻译质量，并且拥有 DeepSeek API key 的用户。

你可以任选一种方式配置 key：

- 设置环境变量：`DEEPSEEK_API_KEY`
- 或在程序的 `Key file` 输入框中选择一个保存 key 的文本文件

推荐配置：

- `API URL`: `https://api.deepseek.com`
- `Model`: `deepseek-chat`

#### xAI / Grok

适合需要使用 xAI / Grok 进行在线翻译的用户。

你可以任选一种方式配置 key：

- 设置环境变量：`XAI_API_KEY`
- 或在程序的 `Key file` 输入框中选择一个保存 key 的文本文件

推荐配置：

- `API URL`: `https://api.x.ai/v1`
- `Model`: `grok-4`

#### 本地免费模式

本地模式使用 Tesseract OCR 和 Argos / LibreTranslate 本地翻译模型，不需要 OpenAI、DeepSeek 或 xAI API key。

从源码运行时可以执行：

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

第一次安装可能较慢，因为需要安装或下载本地翻译模型。

### 从源码运行

环境要求：

- Windows
- Python 3.10 或更新版本
- Tesseract OCR

安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

使用 DeepSeek：

```powershell
$env:DEEPSEEK_API_KEY = "your_deepseek_api_key"
.\start_translator_deepseek.ps1
```

使用 xAI / Grok：

```powershell
$env:XAI_API_KEY = "your_xai_api_key"
.\start_translator_grok.ps1
```

使用本地模式：

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

### 打包 EXE

构建单文件 Windows 可执行程序：

```powershell
.\build_galgame_dialogue_translator_exe.ps1
```

输出文件：

```text
dist\GalgameDialogueTranslator.exe
```

### API Key 文件

推荐使用环境变量：

- `DEEPSEEK_API_KEY`
- `XAI_API_KEY`

也可以把 key 保存到普通文本文件中，然后在程序的 `Key file` 输入框中选择该文件。

不要把 API key 文件提交到 Git。

### OCR 稳定性

如果同一句话反复刷新多个译文：

- 将 `Stable reads` 调高到 `4` 或 `5`。
- 如果已经安装 Tesseract，尽量将 `OCR` 设为 `tesseract`。
- 缩小字幕裁剪区域，只保留真正的对话文字。

如果翻译反应太慢，可以把 `Stable reads` 降到 `2` 或 `3`。

### 注意事项

- 推荐使用窗口化或无边框窗口模式。
- 独占全屏可能无法正常截图。
- OCR 准确率受字体大小、对比度、字幕位置影响很大。
- 在线翻译后端需要可用的 API key 和网络连接。
- 本地翻译质量通常不如在线大模型自然。

## English README

GalgameDialogueTranslator is a Windows overlay translator for visual novels, galgames, and other dialogue-heavy games.

It captures a selected subtitle area from the game window, runs OCR, sends the recognized text to a translation backend, and displays the translated text in a separate always-on-top window. It does not modify game files, inject into the game process, or patch memory.

### Quick Start

Most users should use the packaged release instead of running from source.

1. Download `GalgameDialogueTranslator.exe` from the GitHub Release page.
2. Install [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) if OCR does not work.
3. Double-click `GalgameDialogueTranslator.exe`.
4. Open your game in windowed or borderless-window mode.
5. In the app:
   - Set `Window title` to part of your game window title.
   - Set `OCR` to `auto` or `tesseract`.
   - Set `Translator` to `deepseek`, `grok`, `argos`, or `libretranslate`.
   - Click `Place beside game`.
   - Click `Start`.

If the captured area is wrong, adjust the subtitle crop ratios near the bottom of the window.

### Translation Backends

#### DeepSeek

Use this when you want online translation quality with a DeepSeek API key.

Set either:

- Environment variable: `DEEPSEEK_API_KEY`
- Or a key file path in the app's `Key file` field

Recommended values:

- `API URL`: `https://api.deepseek.com`
- `Model`: `deepseek-chat`

#### xAI / Grok

Use this when you want online translation with an xAI API key.

Set either:

- Environment variable: `XAI_API_KEY`
- Or a key file path in the app's `Key file` field

Recommended values:

- `API URL`: `https://api.x.ai/v1`
- `Model`: `grok-4`

#### Local / Free Mode

Local mode uses Tesseract OCR and local Argos / LibreTranslate models. It does not require an OpenAI, DeepSeek, or xAI API key.

For source users, run:

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

The first setup may take time because local translation models need to be installed or downloaded.

### Run From Source

Requirements:

- Windows
- Python 3.10 or newer
- Tesseract OCR

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run with DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY = "your_deepseek_api_key"
.\start_translator_deepseek.ps1
```

Run with xAI / Grok:

```powershell
$env:XAI_API_KEY = "your_xai_api_key"
.\start_translator_grok.ps1
```

Run local mode:

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

### Build The EXE

To build a single-file Windows executable:

```powershell
.\build_galgame_dialogue_translator_exe.ps1
```

Output:

```text
dist\GalgameDialogueTranslator.exe
```

### API Key Files

Environment variables are recommended:

- `DEEPSEEK_API_KEY`
- `XAI_API_KEY`

You can also put your key in a plain text file and select that file in the app's `Key file` field.

Do not commit API key files to Git.

### OCR Stability

If the translation flickers or updates multiple times for the same line:

- Increase `Stable reads` to `4` or `5`.
- Keep `OCR` set to `tesseract` if Tesseract is installed.
- Tighten the subtitle crop area so it captures only dialogue text.

If translations feel delayed, lower `Stable reads` to `2` or `3`.

### Notes

- Windowed or borderless-window game mode is recommended.
- Exclusive fullscreen may fail to capture correctly.
- OCR accuracy depends heavily on font size, contrast, and crop area.
- Online backends require valid API keys and network access.
- Local translation quality may be less natural than paid online models.

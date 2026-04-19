# GalgameDialogueTranslator

> **AI generated project notice:** This project was generated entirely with AI assistance.
>
> **项目标记：本项目完全使用 AI 生成。**

GalgameDialogueTranslator is a Windows overlay translator for visual novels and other dialogue-heavy games.
It captures a selected subtitle area from the game window, runs OCR, sends the recognized text to a translation backend, and displays the translated text in a separate always-on-top window.

The tool does not modify game files, patch memory, or inject into the game process.

## Quick Start

For most users, use the packaged release instead of running from source.

1. Download `GalgameDialogueTranslator.exe` from the latest GitHub release.
2. Install [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) if OCR does not work.
3. Double-click `GalgameDialogueTranslator.exe`.
4. Open your game in windowed or borderless-window mode.
5. In the app:
   - Set `Window title` to part of your game window title.
   - Set `OCR` to `auto` or `tesseract`.
   - Set `Translator` to `deepseek`, `grok`, `argos`, or `libretranslate`.
   - Click `Place beside game`.
   - Click `Start`.

If the app captures the wrong area, adjust the subtitle crop ratios near the bottom of the window.

## Translation Backends

### DeepSeek

Use this when you want online translation quality with a DeepSeek API key.

Set either:

- Environment variable: `DEEPSEEK_API_KEY`
- Or a key file path in the app's `Key file` field

Recommended values:

- `API URL`: `https://api.deepseek.com`
- `Model`: `deepseek-chat`

### xAI / Grok

Use this when you want online translation with an xAI API key.

Set either:

- Environment variable: `XAI_API_KEY`
- Or a key file path in the app's `Key file` field

Recommended values:

- `API URL`: `https://api.x.ai/v1`
- `Model`: `grok-4`

### Local / Free Mode

Local mode uses Tesseract OCR and local Argos/LibreTranslate models. It does not require an OpenAI, DeepSeek, or xAI API key.

For source users, run:

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

The first setup may take time because translation models need to be installed or downloaded.

## Run From Source

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

Run with xAI/Grok:

```powershell
$env:XAI_API_KEY = "your_xai_api_key"
.\start_translator_grok.ps1
```

Run local mode:

```powershell
.\install_local_stack.ps1
.\start_translator_local.ps1
```

## Build The EXE

To build a single-file Windows executable:

```powershell
.\build_galgame_dialogue_translator_exe.ps1
```

The output file will be:

```text
dist\GalgameDialogueTranslator.exe
```

## Key Files

You can use environment variables, which is the simplest option:

- `DEEPSEEK_API_KEY`
- `XAI_API_KEY`

You can also put your key in a plain text file and select that file in the app's `Key file` field.

Do not commit API key files to Git.

## OCR Stability

If the translation flickers or updates multiple times for the same line:

- Increase `Stable reads` to `4` or `5`.
- Keep `OCR` set to `tesseract` if Tesseract is installed.
- Tighten the subtitle crop area so it captures only dialogue text.

If translations feel delayed, lower `Stable reads` to `2` or `3`.

## Notes

- Windowed or borderless-window game mode is recommended.
- Exclusive fullscreen may fail to capture correctly.
- OCR accuracy depends heavily on font size, contrast, and crop area.
- Online backends require valid API keys and network access.
- Local translation quality may be less natural than paid online models.

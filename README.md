# GalgameDialogueTranslator

External Windows overlay translator for `Little Busters! English Edition`.

This tool does not modify game files or inject into the game process. It captures the subtitle area from the game window, runs OCR, translates the text, and shows the Chinese translation in a separate always-on-top window.

## Fully Local Free Setup

This setup uses:

- Tesseract OCR for English text recognition.
- LibreTranslate/Argos local models for English-to-Chinese translation.

No OpenAI API key is required.

## Install

Open PowerShell in this folder:

```powershell
cd F:\Work\UnrealProjects\Providence\Scripts\realtime_translator
.\install_local_stack.ps1
```

The install script will:

- Install Tesseract OCR with `winget` if it is missing.
- Create `.venv-libretranslate`.
- Install LibreTranslate into that virtual environment.

If Tesseract is installed but not visible in the current shell, open a new PowerShell window or add this path to `PATH`:

```powershell
C:\Program Files\Tesseract-OCR
```

## Run

Use two PowerShell windows.

Start the overlay translator:

```powershell
cd F:\Work\UnrealProjects\Providence\Scripts\realtime_translator
.\start_translator_local.ps1
```

In the overlay:

1. Click `贴到游戏旁`.
2. Click `开始`.
3. If OCR misses text, adjust the subtitle area ratios.

## Manual Command

```powershell
python .\realtime_game_translator.py `
    --title "Little Busters! English Edition" `
    --ocr-engine tesseract `
    --translator argos `
    --libre-url "http://127.0.0.1:5000" `
    --libre-target zh-Hans
```

If you specifically want the HTTP service, run `.\start_libretranslate.ps1` and choose `libretranslate` in the overlay. On this machine, the direct `argos` backend is the verified path.

## DeepSeek Backend

To use DeepSeek for better translation quality while keeping Tesseract OCR local:

```powershell
cd F:\Work\UnrealProjects\Providence\Scripts\realtime_translator
.\start_translator_deepseek.ps1
```

The script reads the API key from:

```text
C:\Users\Administrator\Desktop\Deepseek Key.txt
```

You can also set `DEEPSEEK_API_KEY` in the environment instead of using the key file.

## Grok Backend

To use xAI/Grok with Tesseract OCR:

```powershell
cd F:\Work\UnrealProjects\Providence\Scripts\realtime_translator
.\start_translator_grok.ps1
```

The script reads the API key from:

```text
C:\Users\Administrator\Desktop\Grok Key.txt
```

It uses:

- Base URL: `https://api.x.ai/v1`
- Model: `grok-4`
- Backend: `--translator grok`

The API URL and model selector are linked in the UI. If the API URL contains `api.x.ai`, the provider switches to Grok and the model dropdown shows Grok models. If the API URL contains `deepseek`, the provider switches to DeepSeek and the dropdown shows DeepSeek models.

There is only one API key file input in the UI. Use the Grok key file for `https://api.x.ai/v1` and the DeepSeek key file for `https://api.deepseek.com`.

The overlay also has two quality controls:

- `Context`: how many recent OCR dialogue lines are sent as context.
- `Stable reads`: how many identical OCR reads are required before refreshing the displayed translation. Increase this if the translation text flickers.

## Notes

- Use windowed or borderless game mode. Exclusive fullscreen may not capture correctly.
- LibreTranslate model download may take time on the first run.
- Translation quality is free/local, so it may be less natural than commercial APIs.

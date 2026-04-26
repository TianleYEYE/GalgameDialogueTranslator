# Agent Guide

This repository contains `GalgameDialogueTranslator`, a Windows desktop overlay translator for visual novels and other dialogue-heavy games.

## Project Shape

- Main application logic: `realtime_game_translator.py`
- Packaged app entry point: `galgame_dialogue_translator.py`
- Windows build script: `build_galgame_dialogue_translator_exe.ps1`
- PyInstaller spec: `GalgameDialogueTranslator.spec`
- Source run scripts:
  - `start_translator_openai.ps1`
  - `start_translator_local.ps1`
  - `start_translator_deepseek.ps1`
  - `start_translator_grok.ps1`
  - `start_libretranslate.ps1`
- User documentation: `README.md`

## Important Behavior

- The app should stay generic. Do not hard-code a specific game title, game path, Steam app id, or user machine path.
- Users should be able to select any visible game window through the window list or by entering part of a window title.
- Online DeepSeek/Grok translation performs a one-time Wikipedia context lookup per selected window title. Keep this cached and non-blocking beyond the first lookup where possible.
- Character-name consistency is handled through translation prompt context. Preserve this rule when changing prompt construction.
- The tool must not modify game files, inject into game processes, or patch memory.
- Keep API keys out of source control. Use environment variables or user-selected key files.
- Preserve the notice in `README.md` that the project was generated entirely with AI assistance.

## Development Setup

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

The local translation stack uses `.venv-libretranslate`; do not commit that directory.

## Verification

There is currently no formal pytest suite. Use these checks before committing:

```powershell
.\.venv-libretranslate\Scripts\python.exe -m py_compile .\realtime_game_translator.py .\galgame_dialogue_translator.py
```

If `.venv-libretranslate` is unavailable, use:

```powershell
python -m py_compile .\realtime_game_translator.py .\galgame_dialogue_translator.py
```

For packaging changes, run:

```powershell
.\build_galgame_dialogue_translator_exe.ps1
```

Expected output:

```text
dist\GalgameDialogueTranslator.exe
```

If PyInstaller cannot overwrite the EXE, stop any running `GalgameDialogueTranslator.exe` process and rebuild.

## Git Hygiene

Do not commit:

- `.venv-libretranslate/`
- `build/`
- `dist/`
- `__pycache__/`
- `*.log`
- API key files

These are covered by `.gitignore`; keep that behavior intact.

## Release Notes

When creating a GitHub release:

1. Build `dist\GalgameDialogueTranslator.exe`.
2. Compute SHA256:

```powershell
Get-FileHash -Algorithm SHA256 .\dist\GalgameDialogueTranslator.exe
```

3. Attach the EXE to the release.
4. Include the SHA256 in the release body.

## Documentation Expectations

- Keep `README.md` bilingual.
- Use GitHub-compatible Markdown only; README JavaScript will not run.
- Keep the top language links working.
- Avoid local absolute paths in documentation.
- Use beginner-friendly instructions first, source/build instructions later.

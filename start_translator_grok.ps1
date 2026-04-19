$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:Path += ';C:\Program Files\Tesseract-OCR'
$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

& $Python .\realtime_game_translator.py `
    --title "Little Busters! English Edition" `
    --ocr-engine tesseract `
    --translator grok `
    --target-language "Simplified Chinese" `
    --model "grok-4" `
    --api-url "https://api.x.ai/v1" `
    --api-key-file "C:\Users\Administrator\Desktop\Grok Key.txt" `
    --context-lines 6 `
    --stable-reads 2

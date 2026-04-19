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
    --translator deepseek `
    --target-language "Simplified Chinese" `
    --model "deepseek-chat" `
    --api-url "https://api.deepseek.com" `
    --api-key-file "C:\Users\Administrator\Desktop\Deepseek Key.txt"

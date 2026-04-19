$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:Path += ';C:\Program Files\Tesseract-OCR'
$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

$KeyFile = $env:GROK_API_KEY_FILE
if (-not $KeyFile) {
    $KeyFile = Join-Path $env:USERPROFILE 'Desktop\Grok Key.txt'
}

& $Python .\realtime_game_translator.py `
    --ocr-engine tesseract `
    --translator grok `
    --target-language "Simplified Chinese" `
    --model "grok-4" `
    --api-url "https://api.x.ai/v1" `
    --api-key-file $KeyFile `
    --context-lines 6 `
    --stable-reads 2

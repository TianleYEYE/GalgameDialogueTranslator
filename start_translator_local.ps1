$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:Path += ';C:\Program Files\Tesseract-OCR'
$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

& $Python .\realtime_game_translator.py `
    --ocr-engine tesseract `
    --translator argos `
    --libre-url "http://127.0.0.1:5000" `
    --libre-target zh-Hans

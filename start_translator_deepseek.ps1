$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:Path += ';C:\Program Files\Tesseract-OCR'
$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

$ApiKey = $env:DEEPSEEK_API_KEY

& $Python .\realtime_game_translator.py `
    --ocr-engine tesseract `
    --translator deepseek `
    --target-language "Simplified Chinese" `
    --model "deepseek-v4-flash" `
    --api-url "https://api.deepseek.com" `
    --api-key $ApiKey

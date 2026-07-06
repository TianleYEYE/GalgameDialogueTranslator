$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:Path += ';C:\Program Files\Tesseract-OCR'
$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

$ApiKey = $env:OPENAI_API_KEY

& $Python .\realtime_game_translator.py `
    --ocr-engine tesseract `
    --translator openai `
    --target-language "Simplified Chinese" `
    --model "gpt-5-mini" `
    --api-url "https://api.openai.com/v1" `
    --api-key $ApiKey `
    --context-lines 6 `
    --stable-reads 3

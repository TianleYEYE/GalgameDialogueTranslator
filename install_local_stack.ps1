$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir '.venv-libretranslate'

Write-Host 'Checking Tesseract OCR...'
$tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tesseract) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'winget was not found. Install Tesseract OCR manually, then rerun this script.'
    }

    Write-Host 'Installing Tesseract OCR with winget...'
    winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements

    $env:Path += ';C:\Program Files\Tesseract-OCR'
    $tesseract = Get-Command tesseract -ErrorAction SilentlyContinue
    if (-not $tesseract) {
        Write-Warning 'Tesseract was installed but is not visible in this shell yet. Open a new PowerShell or add C:\Program Files\Tesseract-OCR to PATH.'
    }
}

Write-Host 'Preparing LibreTranslate virtual environment...'
if (-not (Test-Path -LiteralPath $VenvDir)) {
    python -m venv $VenvDir
}

$Python = Join-Path $VenvDir 'Scripts\python.exe'
& $Python -m pip install --upgrade pip
& $Python -m pip install libretranslate
& $Python -m pip install -r (Join-Path $ScriptDir 'requirements.txt')

Write-Host ''
Write-Host 'Local translation stack is prepared.'
Write-Host 'Next: run .\start_translator_local.ps1 in this folder.'

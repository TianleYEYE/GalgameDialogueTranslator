$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Python = Join-Path $ScriptDir '.venv-libretranslate\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = 'python'
}

& $Python -m pip install pyinstaller

$BuildDir = Join-Path $ScriptDir 'build'
$DistDir = Join-Path $ScriptDir 'dist'

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --noupx `
    --name "GalgameDialogueTranslator" `
    --collect-submodules win32com `
    --hidden-import win32timezone `
    --hidden-import PIL.Image `
    --hidden-import PIL.ImageOps `
    --distpath $DistDir `
    --workpath $BuildDir `
    .\galgame_dialogue_translator.py

Write-Host ''
Write-Host 'Built:'
Write-Host (Join-Path $DistDir 'GalgameDialogueTranslator.exe')

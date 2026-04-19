$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Exe = Join-Path $ScriptDir '.venv-libretranslate\Scripts\libretranslate.exe'

if (-not (Test-Path -LiteralPath $Exe)) {
    throw 'LibreTranslate is not installed. Run .\install_local_stack.ps1 first.'
}

Write-Host 'Starting LibreTranslate on http://127.0.0.1:5000 ...'
Write-Host 'Keep this window open while translating.'
& $Exe --host 127.0.0.1 --port 5000 --load-only en,zh --update-models --disable-files-translation

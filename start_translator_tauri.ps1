$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required to run the Tauri + Vue app."
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw "Rust/Cargo is required to run Tauri. Install Rust first, then rerun this script."
}

npm install
npm run tauri dev

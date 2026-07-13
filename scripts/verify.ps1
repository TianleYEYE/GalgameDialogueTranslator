$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    npm test
    npm run build
    cargo test --manifest-path .\src-tauri\Cargo.toml
    cargo check --manifest-path .\src-tauri\Cargo.toml
    python -m py_compile .\translator_cli.py .\realtime_game_translator.py .\galgame_dialogue_translator.py
} finally {
    Pop-Location
}

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::{Command, Output};
use tauri::{AppHandle, Manager};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct TranslateRequest {
    text: String,
    translator: String,
    target_language: String,
    model: String,
    api_url: String,
    api_key: String,
    libre_url: String,
    libre_target: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OcrTranslateRequest {
    window_title: String,
    translator: String,
    target_language: String,
    model: String,
    api_url: String,
    api_key: String,
    libre_url: String,
    libre_target: String,
    ocr_engine: String,
    left: f64,
    top: f64,
    right: f64,
    bottom: f64,
}

#[derive(Debug, Serialize)]
struct TranslateResponse {
    source: String,
    translation: String,
}

#[derive(Debug, Deserialize)]
struct CliTranslateResponse {
    #[serde(default)]
    source: String,
    translation: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct WindowOption {
    title: String,
    hwnd: isize,
    label: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct WindowListResponse {
    windows: Vec<WindowOption>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CollectVocabularyRequest {
    source: String,
    translation: String,
    source_language: String,
    target_language: String,
    window_title: String,
    kind: String,
    note: String,
    tags: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SelectAreaRequest {
    window_title: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PreviewAreaRequest {
    window_title: String,
    left: f64,
    top: f64,
    right: f64,
    bottom: f64,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
struct PreviewAreaResponse {
    data_url: String,
    width: u32,
    height: u32,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SelectAreaResponse {
    cancelled: bool,
    #[serde(default)]
    left: f64,
    #[serde(default)]
    top: f64,
    #[serde(default)]
    right: f64,
    #[serde(default)]
    bottom: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct BasicOkResponse {
    ok: bool,
}

fn bridge_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let mut candidates = Vec::new();

    if let Ok(current_dir) = std::env::current_dir() {
        candidates.push(current_dir.clone());
        candidates.push(current_dir.join("_up_"));
    }

    if let Ok(resource_dir) = app.path().resource_dir() {
        candidates.push(resource_dir.clone());
        candidates.push(resource_dir.join("_up_"));
        if let Some(parent) = resource_dir.parent() {
            candidates.push(parent.join("_up_"));
        }
    }

    for candidate in &candidates {
        if candidate.join("translator_cli.py").exists() {
            return Ok(candidate.clone());
        }
    }

    let checked = candidates
        .iter()
        .map(|path| path.join("translator_cli.py").display().to_string())
        .collect::<Vec<_>>()
        .join("; ");
    Err(format!(
        "translator_cli.py was not found in the working directory or bundled resources. Checked: {checked}"
    ))
}

fn python_command(app: &AppHandle) -> Result<Command, String> {
    let python = std::env::var("PYTHON").unwrap_or_else(|_| "python".to_string());
    let mut command = Command::new(python);
    command.arg("translator_cli.py");
    command.current_dir(bridge_dir(app)?);
    Ok(command)
}

fn run_python(mut command: Command) -> Result<Output, String> {
    let output = command
        .output()
        .map_err(|error| format!("Failed to start Python translator: {error}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
        return Err(if stderr.is_empty() { stdout } else { stderr });
    }

    Ok(output)
}

fn parse_json<T: for<'de> Deserialize<'de>>(output: Output) -> Result<T, String> {
    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(stdout.trim()).map_err(|error| format!("Invalid translator response: {error}"))
}

fn add_translate_args(command: &mut Command, request: &TranslateRequest) {
    command
        .arg("--text")
        .arg(&request.text)
        .arg("--translator")
        .arg(&request.translator)
        .arg("--target-language")
        .arg(&request.target_language)
        .arg("--model")
        .arg(&request.model)
        .arg("--api-url")
        .arg(&request.api_url)
        .arg("--api-key")
        .arg(&request.api_key)
        .arg("--libre-url")
        .arg(&request.libre_url)
        .arg("--libre-target")
        .arg(&request.libre_target);
}

#[tauri::command]
fn translate_text_command(app: AppHandle, request: TranslateRequest) -> Result<TranslateResponse, String> {
    let mut command = python_command(&app)?;
    command.arg("translate");
    add_translate_args(&mut command, &request);

    let parsed: CliTranslateResponse = parse_json(run_python(command)?)?;
    Ok(TranslateResponse {
        source: parsed.source,
        translation: parsed.translation,
    })
}

#[tauri::command]
fn list_windows_command(app: AppHandle) -> Result<WindowListResponse, String> {
    let mut command = python_command(&app)?;
    command.arg("list-windows");
    parse_json(run_python(command)?)
}

#[tauri::command]
fn ocr_translate_command(app: AppHandle, request: OcrTranslateRequest) -> Result<TranslateResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("ocr-translate")
        .arg("--text")
        .arg("")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--translator")
        .arg(&request.translator)
        .arg("--target-language")
        .arg(&request.target_language)
        .arg("--model")
        .arg(&request.model)
        .arg("--api-url")
        .arg(&request.api_url)
        .arg("--api-key")
        .arg(&request.api_key)
        .arg("--libre-url")
        .arg(&request.libre_url)
        .arg("--libre-target")
        .arg(&request.libre_target)
        .arg("--ocr-engine")
        .arg(&request.ocr_engine)
        .arg("--left")
        .arg(request.left.to_string())
        .arg("--top")
        .arg(request.top.to_string())
        .arg("--right")
        .arg(request.right.to_string())
        .arg("--bottom")
        .arg(request.bottom.to_string());

    let parsed: CliTranslateResponse = parse_json(run_python(command)?)?;
    Ok(TranslateResponse {
        source: parsed.source,
        translation: parsed.translation,
    })
}

#[tauri::command]
fn collect_vocabulary_command(app: AppHandle, request: CollectVocabularyRequest) -> Result<BasicOkResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("collect")
        .arg("--source")
        .arg(&request.source)
        .arg("--translation")
        .arg(&request.translation)
        .arg("--source-language")
        .arg(&request.source_language)
        .arg("--target-language")
        .arg(&request.target_language)
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--kind")
        .arg(&request.kind)
        .arg("--note")
        .arg(&request.note)
        .arg("--tags")
        .arg(&request.tags);

    parse_json(run_python(command)?)
}

#[tauri::command]
fn select_area_command(app: AppHandle, request: SelectAreaRequest) -> Result<SelectAreaResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("select-area")
        .arg("--window-title")
        .arg(&request.window_title);

    parse_json(run_python(command)?)
}

#[tauri::command]
fn preview_area_command(app: AppHandle, request: PreviewAreaRequest) -> Result<PreviewAreaResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("preview-area")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--left")
        .arg(request.left.to_string())
        .arg("--top")
        .arg(request.top.to_string())
        .arg("--right")
        .arg(request.right.to_string())
        .arg("--bottom")
        .arg(request.bottom.to_string());

    parse_json(run_python(command)?)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            translate_text_command,
            list_windows_command,
            ocr_translate_command,
            collect_vocabulary_command,
            select_area_command,
            preview_area_command
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

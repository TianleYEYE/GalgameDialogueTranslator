#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Output};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_utils::config::Color;

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
use windows::Win32::UI::Input::KeyboardAndMouse::{GetAsyncKeyState, VK_LBUTTON};

#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{
    GetWindowDisplayAffinity, SetWindowDisplayAffinity, SetWindowPos, HWND_TOPMOST, SWP_NOACTIVATE,
    SWP_NOMOVE, SWP_NOOWNERZORDER, SWP_NOREDRAW, SWP_NOSENDCHANGING, SWP_NOSIZE,
    WDA_EXCLUDEFROMCAPTURE, WDA_NONE,
};

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

#[cfg(windows)]
fn enforce_native_overlay_topmost(window: &tauri::WebviewWindow) -> Result<(), String> {
    let hwnd = window
        .hwnd()
        .map_err(|error| format!("Failed to get translation overlay HWND: {error}"))?;
    unsafe {
        SetWindowPos(
            hwnd,
            Some(HWND_TOPMOST),
            0,
            0,
            0,
            0,
            SWP_NOMOVE
                | SWP_NOSIZE
                | SWP_NOACTIVATE
                | SWP_NOOWNERZORDER
                | SWP_NOREDRAW
                | SWP_NOSENDCHANGING,
        )
        .map_err(|error| format!("Failed to enforce native overlay topmost state: {error}"))?;
    }
    Ok(())
}

#[cfg(windows)]
fn enforce_native_overlay_capture(
    window: &tauri::WebviewWindow,
    capture_visible: bool,
) -> Result<(), String> {
    let hwnd = window
        .hwnd()
        .map_err(|error| format!("Failed to get translation overlay HWND: {error}"))?;
    unsafe {
        let desired = if capture_visible {
            WDA_NONE
        } else {
            WDA_EXCLUDEFROMCAPTURE
        };
        let mut current = WDA_NONE.0;
        let should_update = GetWindowDisplayAffinity(hwnd, &mut current)
            .map(|_| current != desired.0)
            .unwrap_or(true);
        if should_update {
            SetWindowDisplayAffinity(hwnd, desired).map_err(|error| {
                format!("Failed to update native overlay capture mode: {error}")
            })?;
        }
    }
    Ok(())
}

#[cfg(windows)]
fn primary_mouse_button_is_down() -> bool {
    unsafe { GetAsyncKeyState(VK_LBUTTON.0.into()) < 0 }
}

#[cfg(not(windows))]
fn primary_mouse_button_is_down() -> bool {
    false
}

#[cfg(not(windows))]
fn enforce_native_overlay_topmost(_window: &tauri::WebviewWindow) -> Result<(), String> {
    Ok(())
}

#[cfg(not(windows))]
fn enforce_native_overlay_capture(
    _window: &tauri::WebviewWindow,
    _capture_visible: bool,
) -> Result<(), String> {
    Ok(())
}

fn start_overlay_topmost_keeper(app: AppHandle) {
    std::thread::spawn(move || {
        let mut last_error = String::new();
        loop {
            std::thread::sleep(Duration::from_millis(750));
            let Some(window) = app.get_webview_window("translation-overlay") else {
                continue;
            };
            if window.is_visible().unwrap_or(false) {
                let mut errors = Vec::new();
                let capture_visible = app
                    .state::<OverlayStore>()
                    .0
                    .lock()
                    .ok()
                    .and_then(|state| state.as_ref().map(|request| request.capture_visible))
                    .unwrap_or(false);
                if let Err(error) = enforce_native_overlay_capture(&window, capture_visible) {
                    errors.push(error);
                }
                if !primary_mouse_button_is_down() {
                    if let Err(error) = enforce_native_overlay_topmost(&window) {
                        errors.push(error);
                    }
                }
                let current_error = errors.join("; ");
                if !current_error.is_empty() && current_error != last_error {
                    let _ = app.emit("overlay-maintenance-error", &current_error);
                }
                last_error = current_error;
            }
        }
    });
}

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
    #[serde(default)]
    hwnd: isize,
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

#[derive(Debug, Deserialize)]
struct CliOcrResponse {
    #[serde(default)]
    source: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct WindowOption {
    title: String,
    hwnd: isize,
    label: String,
    #[serde(default)]
    x: i32,
    #[serde(default)]
    y: i32,
    #[serde(default)]
    width: u32,
    #[serde(default)]
    height: u32,
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
    #[serde(default)]
    source_context: String,
    source_language: String,
    target_language: String,
    window_title: String,
    kind: String,
    note: String,
    tags: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct UpdateVocabularyRequest {
    created_at: String,
    source: String,
    #[serde(default)]
    translation: String,
    #[serde(default)]
    status: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DeleteVocabularyRequest {
    created_at: String,
    source: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SelectAreaRequest {
    window_title: String,
    #[serde(default)]
    hwnd: isize,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PreviewAreaRequest {
    window_title: String,
    #[serde(default)]
    hwnd: isize,
    left: f64,
    top: f64,
    right: f64,
    bottom: f64,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OcrTextRequest {
    window_title: String,
    #[serde(default)]
    hwnd: isize,
    ocr_engine: String,
    model: String,
    api_url: String,
    api_key: String,
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

#[derive(Debug, Serialize, Deserialize)]
struct VocabularyListResponse {
    #[serde(default)]
    entries: Vec<serde_json::Value>,
    #[serde(default)]
    count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SettingsResponse {
    settings: serde_json::Value,
    path: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SaveSettingsRequest {
    settings: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
struct OverlayRequest {
    text: String,
    language: String,
    font_family: String,
    font_size: f64,
    #[serde(default)]
    capture_visible: bool,
    x: f64,
    y: f64,
    width: f64,
    height: f64,
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OverlayBoundsResponse {
    visible: bool,
    x: f64,
    y: f64,
    width: f64,
    height: f64,
}

struct OverlayStore(Mutex<Option<OverlayRequest>>);

fn persist_overlay_bounds(
    app: &AppHandle,
    window: &tauri::WebviewWindow,
) -> Result<OverlayBoundsResponse, String> {
    let position = window
        .outer_position()
        .map_err(|error| format!("Failed to read overlay position: {error}"))?;
    let size = window
        .outer_size()
        .map_err(|error| format!("Failed to read overlay size: {error}"))?;
    let bounds = OverlayBoundsResponse {
        visible: window.is_visible().unwrap_or(false),
        x: f64::from(position.x),
        y: f64::from(position.y),
        width: f64::from(size.width),
        height: f64::from(size.height),
    };
    if let Ok(mut state) = app.state::<OverlayStore>().0.lock() {
        if let Some(request) = state.as_mut() {
            request.x = bounds.x;
            request.y = bounds.y;
            request.width = bounds.width;
            request.height = bounds.height;
        }
    }
    let _ = app.emit("overlay-bounds-changed", &bounds);
    Ok(bounds)
}

fn settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    let config_dir = app
        .path()
        .app_config_dir()
        .map_err(|error| format!("Failed to locate app config directory: {error}"))?;
    Ok(config_dir.join("translator_settings.json"))
}

fn vocabulary_path(app: &AppHandle) -> Result<PathBuf, String> {
    let config_dir = app
        .path()
        .app_config_dir()
        .map_err(|error| format!("Failed to locate app config directory: {error}"))?;
    Ok(config_dir.join("vocabulary.jsonl"))
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
    command.env("GDT_VOCABULARY_PATH", vocabulary_path(app)?);
    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);
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
    serde_json::from_str(stdout.trim())
        .map_err(|error| format!("Invalid translator response: {error}"))
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
fn translate_text_command(
    app: AppHandle,
    request: TranslateRequest,
) -> Result<TranslateResponse, String> {
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
fn ocr_translate_command(
    app: AppHandle,
    request: OcrTranslateRequest,
) -> Result<TranslateResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("ocr-translate")
        .arg("--text")
        .arg("")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--hwnd")
        .arg(request.hwnd.to_string())
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
fn ocr_text_command(app: AppHandle, request: OcrTextRequest) -> Result<TranslateResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("ocr")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--hwnd")
        .arg(request.hwnd.to_string())
        .arg("--ocr-engine")
        .arg(&request.ocr_engine)
        .arg("--model")
        .arg(&request.model)
        .arg("--api-url")
        .arg(&request.api_url)
        .arg("--api-key")
        .arg(&request.api_key)
        .arg("--left")
        .arg(request.left.to_string())
        .arg("--top")
        .arg(request.top.to_string())
        .arg("--right")
        .arg(request.right.to_string())
        .arg("--bottom")
        .arg(request.bottom.to_string());

    let parsed: CliOcrResponse = parse_json(run_python(command)?)?;
    Ok(TranslateResponse {
        source: parsed.source,
        translation: String::new(),
    })
}

#[tauri::command]
fn collect_vocabulary_command(
    app: AppHandle,
    request: CollectVocabularyRequest,
) -> Result<BasicOkResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("collect")
        .arg("--source")
        .arg(&request.source)
        .arg("--translation")
        .arg(&request.translation)
        .arg("--source-context")
        .arg(&request.source_context)
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
fn select_area_command(
    app: AppHandle,
    request: SelectAreaRequest,
) -> Result<SelectAreaResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("select-area")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--hwnd")
        .arg(request.hwnd.to_string());

    parse_json(run_python(command)?)
}

#[tauri::command]
fn list_vocabulary_command(app: AppHandle) -> Result<VocabularyListResponse, String> {
    let mut command = python_command(&app)?;
    command.arg("vocabulary");
    parse_json(run_python(command)?)
}

#[tauri::command]
fn update_vocabulary_command(
    app: AppHandle,
    request: UpdateVocabularyRequest,
) -> Result<BasicOkResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("update-vocabulary")
        .arg("--created-at")
        .arg(&request.created_at)
        .arg("--source")
        .arg(&request.source)
        .arg("--translation")
        .arg(&request.translation)
        .arg("--status")
        .arg(&request.status);
    parse_json(run_python(command)?)
}

#[tauri::command]
fn delete_vocabulary_command(
    app: AppHandle,
    request: DeleteVocabularyRequest,
) -> Result<BasicOkResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("delete-vocabulary")
        .arg("--created-at")
        .arg(&request.created_at)
        .arg("--source")
        .arg(&request.source);
    parse_json(run_python(command)?)
}

#[tauri::command]
fn load_settings_command(app: AppHandle) -> Result<SettingsResponse, String> {
    let path = settings_path(&app)?;
    if !path.exists() {
        return Ok(SettingsResponse {
            settings: serde_json::json!({}),
            path: path.display().to_string(),
        });
    }

    let body = fs::read_to_string(&path)
        .map_err(|error| format!("Failed to read settings file {}: {error}", path.display()))?;
    let settings = serde_json::from_str(&body)
        .map_err(|error| format!("Failed to parse settings file {}: {error}", path.display()))?;
    Ok(SettingsResponse {
        settings,
        path: path.display().to_string(),
    })
}

#[tauri::command]
fn save_settings_command(
    app: AppHandle,
    request: SaveSettingsRequest,
) -> Result<BasicOkResponse, String> {
    let path = settings_path(&app)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            format!(
                "Failed to create settings directory {}: {error}",
                parent.display()
            )
        })?;
    }
    let body = serde_json::to_string_pretty(&request.settings)
        .map_err(|error| format!("Failed to serialize settings: {error}"))?;
    fs::write(&path, body)
        .map_err(|error| format!("Failed to write settings file {}: {error}", path.display()))?;
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn show_translation_overlay_command(
    app: AppHandle,
    request: OverlayRequest,
) -> Result<BasicOkResponse, String> {
    let store = app.state::<OverlayStore>();
    *store
        .0
        .lock()
        .map_err(|error| format!("Failed to store translation overlay state: {error}"))? =
        Some(request.clone());
    let overlay = app
        .get_webview_window("translation-overlay")
        .ok_or_else(|| "Translation overlay window was not initialized at startup.".to_string())?;

    // Window operations can wait on WebView2 while this command itself is being
    // dispatched by WebView2. Schedule them on the UI loop and return promptly.
    app.run_on_main_thread(move || {
        let _ = overlay.set_position(tauri::Position::Physical(tauri::PhysicalPosition::new(
            request.x.round() as i32,
            request.y.round() as i32,
        )));
        let _ = overlay.set_size(tauri::Size::Physical(tauri::PhysicalSize::new(
            request.width.max(280.0).round() as u32,
            request.height.max(80.0).round() as u32,
        )));
        let _ = overlay.set_background_color(Some(Color(0, 0, 0, 0)));
        let _ = overlay.set_shadow(false);
        let _ = overlay.set_content_protected(!request.capture_visible);
        let _ = overlay.set_always_on_top(true);
        let _ = overlay.show();
        let _ = enforce_native_overlay_capture(&overlay, request.capture_visible);
        let _ = enforce_native_overlay_topmost(&overlay);
    })
    .map_err(|error| format!("Failed to schedule translation overlay display: {error}"))?;
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn get_translation_overlay_state_command(
    state: State<'_, OverlayStore>,
) -> Result<Option<OverlayRequest>, String> {
    state
        .0
        .lock()
        .map(|value| value.clone())
        .map_err(|error| format!("Failed to read translation overlay state: {error}"))
}

#[tauri::command]
fn update_translation_overlay_command(
    app: AppHandle,
    request: OverlayRequest,
) -> Result<BasicOkResponse, String> {
    let store = app.state::<OverlayStore>();
    *store
        .0
        .lock()
        .map_err(|error| format!("Failed to store translation overlay state: {error}"))? =
        Some(request.clone());
    if let Some(overlay) = app.get_webview_window("translation-overlay") {
        let capture_visible = request.capture_visible;
        app.run_on_main_thread(move || {
            let _ = overlay.set_content_protected(!capture_visible);
            let _ = enforce_native_overlay_capture(&overlay, capture_visible);
        })
        .map_err(|error| format!("Failed to update translation overlay capture mode: {error}"))?;
    }
    // overlay.html polls this state directly, avoiding cross-WebView eval stalls.
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn start_translation_overlay_drag_command(app: AppHandle) -> Result<BasicOkResponse, String> {
    let window = app
        .get_webview_window("translation-overlay")
        .ok_or_else(|| "Translation overlay window was not initialized.".to_string())?;
    window
        .start_dragging()
        .map_err(|error| format!("Failed to start translation overlay drag: {error}"))?;
    persist_overlay_bounds(&app, &window)?;
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn save_translation_overlay_bounds_command(app: AppHandle) -> Result<BasicOkResponse, String> {
    let window = app
        .get_webview_window("translation-overlay")
        .ok_or_else(|| "Translation overlay window was not initialized.".to_string())?;
    persist_overlay_bounds(&app, &window)?;
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn hide_translation_overlay_command(app: AppHandle) -> Result<BasicOkResponse, String> {
    if let Some(window) = app.get_webview_window("translation-overlay") {
        window
            .hide()
            .map_err(|error| format!("Failed to hide translation overlay: {error}"))?;
    }
    let _ = app.emit("overlay-hidden", true);
    Ok(BasicOkResponse { ok: true })
}

#[tauri::command]
fn preview_area_command(
    app: AppHandle,
    request: PreviewAreaRequest,
) -> Result<PreviewAreaResponse, String> {
    let mut command = python_command(&app)?;
    command
        .arg("preview-area")
        .arg("--window-title")
        .arg(&request.window_title)
        .arg("--hwnd")
        .arg(request.hwnd.to_string())
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
        .manage(OverlayStore(Mutex::new(None)))
        .setup(|app| {
            start_overlay_topmost_keeper(app.handle().clone());
            if let Some(overlay) = app.get_webview_window("translation-overlay") {
                let app_handle = app.handle().clone();
                let overlay_window = overlay.clone();
                overlay.on_window_event(move |event| {
                    if matches!(
                        event,
                        tauri::WindowEvent::Moved(_) | tauri::WindowEvent::Resized(_)
                    ) {
                        let _ = persist_overlay_bounds(&app_handle, &overlay_window);
                    }
                });
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            load_settings_command,
            save_settings_command,
            translate_text_command,
            list_windows_command,
            ocr_text_command,
            ocr_translate_command,
            collect_vocabulary_command,
            list_vocabulary_command,
            update_vocabulary_command,
            delete_vocabulary_command,
            select_area_command,
            preview_area_command,
            show_translation_overlay_command,
            get_translation_overlay_state_command,
            update_translation_overlay_command,
            hide_translation_overlay_command,
            start_translation_overlay_drag_command,
            save_translation_overlay_bounds_command
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::OverlayRequest;

    fn base_overlay_json() -> serde_json::Value {
        serde_json::json!({
            "text": "translated line",
            "language": "Simplified Chinese",
            "fontFamily": "Microsoft YaHei UI",
            "fontSize": 24,
            "x": 100,
            "y": 200,
            "width": 640,
            "height": 120
        })
    }

    #[test]
    fn overlay_capture_defaults_to_protected() {
        let request: OverlayRequest = serde_json::from_value(base_overlay_json()).unwrap();
        assert!(!request.capture_visible);
    }

    #[test]
    fn overlay_capture_uses_camel_case_contract() {
        let mut value = base_overlay_json();
        value["captureVisible"] = serde_json::Value::Bool(true);
        let request: OverlayRequest = serde_json::from_value(value).unwrap();
        assert!(request.capture_visible);
        let serialized = serde_json::to_value(request).unwrap();
        assert_eq!(serialized["captureVisible"], true);
    }
}

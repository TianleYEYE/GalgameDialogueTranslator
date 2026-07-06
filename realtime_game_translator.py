import argparse
import base64
import ctypes
import datetime as dt
import io
import json
import locale
import os
import re
import shutil
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from difflib import SequenceMatcher
from tkinter import messagebox, ttk
from typing import Callable
from urllib import error, parse, request

import mss
import pytesseract
import win32con
import win32gui
from PIL import Image, ImageOps
from PIL import ImageTk


def enable_dpi_awareness() -> None:
    """Keep Win32 window coordinates aligned with physical screenshot pixels."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


enable_dpi_awareness()


DEFAULT_TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DEFAULT_OUTPUT_FONT_FAMILY = "Microsoft YaHei UI"
DEFAULT_OUTPUT_FONT_SIZE = 13
LOCAL_CONFIG_FILENAME = "translator_settings.json"
ORIGINAL_OCR_LANGUAGE = "Original OCR"
DEFAULT_OUTPUT_LEFT_LANGUAGE = ORIGINAL_OCR_LANGUAGE
DEFAULT_OUTPUT_RIGHT_LANGUAGE = "Simplified Chinese"
DEFAULT_OUTPUT_LAYOUT = "horizontal"
BASE_WINDOW_TITLE = "Game Dialogue Translator"
DEFAULT_UI_LANGUAGE = "auto"
VOCABULARY_FILENAME = "vocabulary.jsonl"
OUTPUT_LANGUAGE_OPTIONS = (
    ORIGINAL_OCR_LANGUAGE,
    "Simplified Chinese",
    "Traditional Chinese",
    "Japanese",
    "English",
    "Korean",
)
OUTPUT_LAYOUT_OPTIONS = ("horizontal", "vertical")
UI_LANGUAGE_OPTIONS = ("auto", "zh-CN", "en")
OCR_SIMILARITY_THRESHOLD = 0.78
WIKI_USER_AGENT = "GalgameDialogueTranslator/0.1 (https://github.com/TianleYEYE/GalgameDialogueTranslator)"
UI_COLORS = {
    "bg": "#F4EFE6",
    "panel": "#FBF8F2",
    "panel_alt": "#F1E6D2",
    "panel_edge": "#D8C8AE",
    "accent": "#C27A3A",
    "accent_soft": "#E8C49A",
    "ink": "#2B241D",
    "muted": "#75695D",
    "teal": "#557C78",
    "teal_soft": "#DDEAE8",
    "danger": "#A85A43",
}

API_PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": (
            "gpt-5.2",
            "gpt-5-mini",
            "gpt-5.2-codex",
            "gpt-5-codex",
            "gpt-5.1-codex",
            "gpt-5.1-codex-max",
            "gpt-5.2-pro",
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
        ),
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "models": ("deepseek-v4-flash", "deepseek-v4-pro"),
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "models": ("grok-4", "grok-4.20-reasoning", "grok-4-fast", "grok-3", "grok-3-mini"),
    },
}

OUTPUT_LANGUAGE_LABELS = {
    ORIGINAL_OCR_LANGUAGE: {"en": "Original OCR", "zh-CN": "原始 OCR"},
    "Simplified Chinese": {"en": "Simplified Chinese", "zh-CN": "简体中文"},
    "Traditional Chinese": {"en": "Traditional Chinese", "zh-CN": "繁体中文"},
    "Japanese": {"en": "Japanese", "zh-CN": "日语"},
    "English": {"en": "English", "zh-CN": "英语"},
    "Korean": {"en": "Korean", "zh-CN": "韩语"},
}

UI_STRINGS = {
    "en": {
        "app_title": "Game Dialogue Translator",
        "label_window_title": "Window title",
        "button_refresh_windows": "Refresh windows",
        "button_place_beside": "Place beside",
        "label_left_output": "Left output",
        "label_model": "Model",
        "label_right_output": "Right output",
        "label_interval_ms": "Interval ms",
        "button_start": "Start",
        "button_retranslate": "Retranslate",
        "button_stop": "Stop",
        "button_collect_selection": "Collect Selection",
        "button_collect_current": "Collect Current",
        "button_show_advanced": "Advanced & Capture",
        "button_hide_advanced": "Hide Advanced",
        "label_ocr": "OCR",
        "label_translator": "Translator",
        "label_libre_url": "Libre URL",
        "label_libre_target": "Libre target",
        "label_api_url": "API URL",
        "label_api_key": "API Key",
        "button_provider_configs": "Provider configs",
        "button_vocabulary": "Vocabulary",
        "label_font": "Font",
        "label_font_size": "Font size",
        "label_layout": "Layout",
        "label_window_list": "Window list",
        "label_system_language": "System language",
        "label_context": "Context",
        "label_stable_reads": "Stable reads",
        "check_lock_current_line": "Lock current line",
        "reading_stage_title": "Bilingual Reading Stage",
        "reading_stage_subtitle": "Keep the story readable first. Original text and translation stay side by side for quick glance reading.",
        "frame_subtitle_crop_area": "Subtitle crop area",
        "button_select_area": "Select area",
        "crop_left": "Left",
        "crop_top": "Top",
        "crop_right": "Right",
        "crop_bottom": "Bottom",
        "panel_left": "Left",
        "panel_right": "Right",
        "panel_top": "Top",
        "panel_bottom": "Bottom",
        "placeholder_left": "Select a game window, then click Start.\nThe first panel can show original OCR text or a chosen language.",
        "placeholder_right": "The second panel can show another language at the same time.",
        "status_ready": "Ready",
        "status_running": "Running",
        "status_stopped": "Stopped",
        "status_selecting_area": "Drag over the game window to select the subtitle area",
        "status_area_updated": "Capture area updated",
        "status_area_cancelled": "Capture area selection cancelled",
        "status_vocabulary_collected": "Vocabulary collected",
        "status_no_ocr_text": "No OCR text available for translation",
        "status_translating": "Translating",
        "status_updated": "Updated",
        "status_window_not_found": "Window not found",
        "status_same_dialogue": "Same dialogue detected, keeping current output",
        "status_locked_new_dialogue": "New dialogue detected but current line is locked",
        "status_waiting_stable_ocr": "Waiting for stable OCR text",
        "status_no_new_text": "No new text detected",
        "status_error": "Error: {error}",
        "status_reading_ocr": "Reading OCR text from image",
        "status_lookup_wiki": "Looking up wiki context",
        "title_ready": "Ready",
        "title_running": "Running",
        "title_stopped": "Stopped",
        "title_selecting_area": "Selecting area",
        "title_area_updated": "Area updated",
        "title_area_cancelled": "Selection cancelled",
        "title_collected": "Collected",
        "title_idle": "Idle",
        "title_translating": "Translating...",
        "title_window_not_found": "Window not found",
        "title_locked": "Locked",
        "title_waiting_ocr": "Waiting for OCR",
        "title_error": "Error",
        "title_reading_ocr": "Reading OCR...",
        "title_lookup_wiki": "Looking up context...",
        "dialog_provider_configs": "Provider Configs",
        "dialog_vocabulary": "Vocabulary",
        "dialog_collect_vocabulary": "Collect Vocabulary",
        "header_provider": "Provider",
        "header_use": "Use",
        "button_use": "Use",
        "button_save_configs": "Save configs",
        "button_close": "Close",
        "message_window_not_found_title": "Window not found",
        "message_window_not_found_body": "Select a window from the list or enter part of the game window title.",
        "message_select_area_missing_window": "Select a window from the list or enter part of the game window title before selecting an area.",
        "message_no_selection_title": "No selection",
        "message_no_selection_body": "Select text in one of the output panels before collecting.",
        "message_no_current_text_title": "No current text",
        "message_no_current_text_body": "There is no current dialogue to collect yet.",
        "message_missing_source_title": "Missing source",
        "message_missing_source_body": "Source text cannot be empty.",
        "label_source": "Source",
        "label_translation": "Translation",
        "label_kind": "Kind",
        "label_tags": "Tags",
        "label_note": "Note",
        "button_save": "Save",
        "column_created": "Created",
        "column_kind": "Kind",
        "column_source": "Source",
        "column_translation": "Translation",
        "column_tags": "Tags",
        "details_source_language": "Source language",
        "details_target_language": "Target language",
        "details_window": "Window",
        "label_system_language_auto": "Auto",
    },
    "zh-CN": {
        "app_title": "游戏对话翻译器",
        "label_window_title": "窗口标题",
        "button_refresh_windows": "刷新窗口",
        "button_place_beside": "贴边摆放",
        "label_left_output": "左侧输出",
        "label_model": "模型",
        "label_right_output": "右侧输出",
        "label_interval_ms": "轮询间隔 ms",
        "button_start": "开始",
        "button_retranslate": "重新翻译",
        "button_stop": "停止",
        "button_collect_selection": "收藏选中文本",
        "button_collect_current": "收藏当前句",
        "button_show_advanced": "高级与截取",
        "button_hide_advanced": "收起高级项",
        "label_ocr": "OCR",
        "label_translator": "翻译器",
        "label_libre_url": "Libre 地址",
        "label_libre_target": "Libre 目标语",
        "label_api_url": "API 地址",
        "label_api_key": "API Key",
        "button_provider_configs": "Provider 配置",
        "button_vocabulary": "词汇本",
        "label_font": "字体",
        "label_font_size": "字号",
        "label_layout": "布局",
        "label_window_list": "窗口列表",
        "label_system_language": "系统语言",
        "label_context": "上下文",
        "label_stable_reads": "稳定读取次数",
        "check_lock_current_line": "锁定当前句",
        "reading_stage_title": "双语阅读区",
        "reading_stage_subtitle": "先保证剧情阅读顺畅，再顺手看原文和译文。原文与翻译并排展示，适合边玩边看。",
        "frame_subtitle_crop_area": "字幕裁剪区域",
        "button_select_area": "选择区域",
        "crop_left": "左",
        "crop_top": "上",
        "crop_right": "右",
        "crop_bottom": "下",
        "panel_left": "左侧",
        "panel_right": "右侧",
        "panel_top": "上方",
        "panel_bottom": "下方",
        "placeholder_left": "先选择游戏窗口，再点击开始。\n第一个区域可以显示原始 OCR 或你指定的语言。",
        "placeholder_right": "第二个区域可以同时显示另一种语言。",
        "status_ready": "就绪",
        "status_running": "运行中",
        "status_stopped": "已停止",
        "status_selecting_area": "请在游戏窗口上拖拽选择字幕区域",
        "status_area_updated": "截取区域已更新",
        "status_area_cancelled": "已取消区域选择",
        "status_vocabulary_collected": "已收藏到词汇本",
        "status_no_ocr_text": "当前没有可翻译的 OCR 文本",
        "status_translating": "翻译中",
        "status_updated": "已更新",
        "status_window_not_found": "未找到窗口",
        "status_same_dialogue": "检测到相同台词，保持当前显示",
        "status_locked_new_dialogue": "检测到新台词，但当前句已锁定",
        "status_waiting_stable_ocr": "等待 OCR 稳定",
        "status_no_new_text": "未检测到新文本",
        "status_error": "错误：{error}",
        "status_reading_ocr": "正在从图像读取 OCR 文本",
        "status_lookup_wiki": "正在查询 Wiki 上下文",
        "title_ready": "就绪",
        "title_running": "运行中",
        "title_stopped": "已停止",
        "title_selecting_area": "选择区域中",
        "title_area_updated": "区域已更新",
        "title_area_cancelled": "已取消",
        "title_collected": "已收藏",
        "title_idle": "空闲",
        "title_translating": "翻译中...",
        "title_window_not_found": "未找到窗口",
        "title_locked": "已锁定",
        "title_waiting_ocr": "等待 OCR",
        "title_error": "错误",
        "title_reading_ocr": "读取 OCR 中...",
        "title_lookup_wiki": "查询上下文中...",
        "dialog_provider_configs": "Provider 配置",
        "dialog_vocabulary": "词汇本",
        "dialog_collect_vocabulary": "收藏词汇",
        "header_provider": "Provider",
        "header_use": "使用",
        "button_use": "使用",
        "button_save_configs": "保存配置",
        "button_close": "关闭",
        "message_window_not_found_title": "未找到窗口",
        "message_window_not_found_body": "请选择窗口列表中的游戏窗口，或输入部分窗口标题。",
        "message_select_area_missing_window": "请先从窗口列表选择游戏窗口，或输入部分窗口标题，再选择区域。",
        "message_no_selection_title": "未选中文本",
        "message_no_selection_body": "请先在任一输出区域中选中文本再进行收藏。",
        "message_no_current_text_title": "没有当前文本",
        "message_no_current_text_body": "当前还没有可收藏的对话。",
        "message_missing_source_title": "缺少原文",
        "message_missing_source_body": "原文不能为空。",
        "label_source": "原文",
        "label_translation": "译文",
        "label_kind": "类型",
        "label_tags": "标签",
        "label_note": "备注",
        "button_save": "保存",
        "column_created": "创建时间",
        "column_kind": "类型",
        "column_source": "原文",
        "column_translation": "译文",
        "column_tags": "标签",
        "details_source_language": "原文语言",
        "details_target_language": "目标语言",
        "details_window": "窗口",
        "label_system_language_auto": "自动",
    },
}


def detect_api_provider(base_url: str, fallback: str = "") -> str:
    url = base_url.casefold()
    if "api.openai.com" in url or "openai.com" in url:
        return "openai"
    if "api.x.ai" in url or "x.ai" in url:
        return "grok"
    if "deepseek" in url:
        return "deepseek"
    return fallback


def models_for_provider(provider: str) -> tuple[str, ...]:
    return API_PROVIDER_CONFIGS.get(provider, {}).get("models", ())


def local_config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), LOCAL_CONFIG_FILENAME)


def vocabulary_path() -> str:
    configured_path = os.environ.get("GDT_VOCABULARY_PATH", "").strip()
    if configured_path:
        return configured_path
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), VOCABULARY_FILENAME)


def legacy_vocabulary_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), VOCABULARY_FILENAME)


def ensure_vocabulary_file() -> str:
    path = vocabulary_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    legacy_path = legacy_vocabulary_path()
    if path != legacy_path and not os.path.exists(path) and os.path.exists(legacy_path):
        try:
            shutil.copyfile(legacy_path, path)
        except Exception:
            pass
    return path


def detect_system_language() -> str:
    preferred = locale.getdefaultlocale()[0] if locale.getdefaultlocale() else ""
    value = (preferred or "").lower()
    if "zh" in value:
        return "zh-CN"
    return "en"


def configure_tesseract() -> None:
    if shutil.which("tesseract"):
        return
    if os.path.exists(DEFAULT_TESSERACT_EXE):
        pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_EXE
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + os.path.dirname(DEFAULT_TESSERACT_EXE)


def tesseract_is_available() -> bool:
    return shutil.which("tesseract") is not None or os.path.exists(DEFAULT_TESSERACT_EXE)


def canonicalize_ocr_for_compare(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ocr_texts_are_similar(left: str, right: str) -> bool:
    left_key = canonicalize_ocr_for_compare(left)
    right_key = canonicalize_ocr_for_compare(right)
    if not left_key or not right_key:
        return False
    if left_key in right_key or right_key in left_key:
        shorter = min(len(left_key), len(right_key))
        longer = max(len(left_key), len(right_key))
        return shorter >= 10 and shorter / longer >= 0.55
    return SequenceMatcher(None, left_key, right_key).ratio() >= OCR_SIMILARITY_THRESHOLD


def ocr_text_quality_score(text: str) -> tuple[int, int, int]:
    letters = sum(char.isalpha() for char in text)
    words = len(re.findall(r"[A-Za-z]{2,}", text))
    noise = len(re.findall(r"[^A-Za-z0-9\s,.!?;:'\"-]", text))
    return (words, letters - noise * 4, -len(text))


def clean_work_title(window_title: str) -> str:
    title = re.sub(r"\s+\[[0-9]+\]$", "", window_title).strip()
    title = re.sub(r"\s+-\s+(Steam|Unity|Ren'Py|NW.js|Google Chrome|Microsoft Edge)$", "", title, flags=re.I)
    title = re.sub(r"\s+\(.*?\)$", "", title).strip()
    return title or window_title.strip()


def fetch_wiki_context(work_title: str) -> str:
    query = clean_work_title(work_title)
    if not query:
        return ""
    try:
        search_url = "https://en.wikipedia.org/w/api.php?" + parse.urlencode(
            {
                "action": "query",
                "list": "search",
                "srsearch": f"{query} visual novel game",
                "srlimit": "3",
                "format": "json",
                "utf8": "1",
            }
        )
        search_req = request.Request(search_url, headers={"User-Agent": WIKI_USER_AGENT})
        with request.urlopen(search_req, timeout=8) as response:
            search_body = json.loads(response.read().decode("utf-8"))
        results = search_body.get("query", {}).get("search", [])
        if not results:
            return ""

        page_title = str(results[0].get("title", "")).strip()
        if not page_title:
            return ""

        page_url = "https://en.wikipedia.org/w/api.php?" + parse.urlencode(
            {
                "action": "query",
                "prop": "extracts|links",
                "exintro": "1",
                "explaintext": "1",
                "pllimit": "50",
                "titles": page_title,
                "format": "json",
                "utf8": "1",
            }
        )
        page_req = request.Request(page_url, headers={"User-Agent": WIKI_USER_AGENT})
        with request.urlopen(page_req, timeout=8) as response:
            page_body = json.loads(response.read().decode("utf-8"))

        pages = page_body.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {}) if pages else {}
        summary = re.sub(r"\s+", " ", str(page.get("extract", "")).strip())
        if len(summary) > 900:
            summary = summary[:900].rsplit(" ", 1)[0] + "..."

        links = []
        blocked = {"visual novel", "windows", "steam", "playstation", "nintendo switch", "anime", "manga"}
        for link in page.get("links", [])[:50]:
            name = str(link.get("title", "")).strip()
            if not name or ":" in name or name.casefold() in blocked:
                continue
            if len(name) <= 48:
                links.append(name)
            if len(links) >= 18:
                break

        parts = [f"Work title from selected window: {query}"]
        if page_title.casefold() != query.casefold():
            parts.append(f"Matched wiki page: {page_title}")
        if summary:
            parts.append(f"Wiki summary: {summary}")
        if links:
            parts.append("Potentially relevant names/terms from wiki: " + "; ".join(links))
        return "\n".join(parts)
    except Exception as exc:
        return f"Wiki lookup unavailable for {query}: {exc}"


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    rect: tuple[int, int, int, int]


def window_capture_rect(hwnd: int) -> tuple[int, int, int, int]:
    """Return the visible client area used for selection, preview and OCR."""
    try:
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        screen_left, screen_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        screen_right, screen_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        if screen_right - screen_left >= 20 and screen_bottom - screen_top >= 20:
            return screen_left, screen_top, screen_right, screen_bottom
    except Exception:
        pass
    return win32gui.GetWindowRect(hwnd)


def find_window(title_part: str) -> WindowInfo | None:
    needle = title_part.casefold().strip()
    for window in list_capture_windows():
        if not needle or needle in window.title.casefold():
            return window
    return None


def find_window_by_reference(title_part: str = "", hwnd: int | None = None) -> WindowInfo | None:
    windows = list_capture_windows()
    if hwnd:
        for window in windows:
            if window.hwnd == hwnd:
                return window

    needle = title_part.casefold().strip()
    if not needle:
        return windows[0] if windows else None

    for window in windows:
        if needle in window.title.casefold() or window.title.casefold() in needle:
            return window

    normalized_needle = re.sub(r"\s+", " ", needle)
    for window in windows:
        normalized_title = re.sub(r"\s+", " ", window.title.casefold())
        if normalized_needle in normalized_title or normalized_title in normalized_needle:
            return window
    return None


def list_capture_windows() -> list[WindowInfo]:
    blocked_titles = {"Program Manager", "Game Dialogue Translator", "GalgameDialogueTranslator"}
    windows: list[WindowInfo] = []

    def visit(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd).strip()
        if not title or title in blocked_titles:
            return True
        left, top, right, bottom = window_capture_rect(hwnd)
        if right - left >= 240 and bottom - top >= 160:
            windows.append(WindowInfo(hwnd, title, (left, top, right, bottom)))
        return True

    win32gui.EnumWindows(visit, None)
    return windows


def clamp_ratio(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def capture_window_image(window: WindowInfo) -> Image.Image:
    left, top, right, bottom = window_capture_rect(window.hwnd)
    monitor = {
        "left": left,
        "top": top,
        "width": max(right - left, 20),
        "height": max(bottom - top, 20),
    }
    with mss.mss() as capture:
        grabbed = capture.grab(monitor)
    return Image.frombytes("RGB", grabbed.size, grabbed.rgb)


def select_region_for_window(
    root: tk.Tk,
    window: WindowInfo,
    on_selected: Callable[[tuple[float, float, float, float]], None],
    on_cancelled: Callable[[], None],
) -> None:
    screenshot = capture_window_image(window)
    image_width = max(screenshot.width, 1)
    image_height = max(screenshot.height, 1)
    max_width = max(root.winfo_screenwidth() - 120, 480)
    max_height = max(root.winfo_screenheight() - 160, 320)
    scale = min(max_width / image_width, max_height / image_height, 1.0)
    width = max(int(image_width * scale), 1)
    height = max(int(image_height * scale), 1)
    display_image = screenshot.resize((width, height), Image.Resampling.LANCZOS) if scale < 1 else screenshot
    photo = ImageTk.PhotoImage(display_image)

    selector = tk.Toplevel(root)
    selector.attributes("-topmost", True)
    selector.title("Select subtitle area")
    selector.configure(bg="#111111")
    selector.geometry(f"{width}x{height}")
    selector.focus_force()
    selector.grab_set()

    canvas = tk.Canvas(selector, cursor="crosshair", bg="black", highlightthickness=0, width=width, height=height)
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor="nw", image=photo)
    canvas.image = photo
    canvas.create_text(
        width // 2,
        28,
        text="Drag to select subtitle area. Right click or Esc to cancel.",
        fill="white",
        font=("Segoe UI", 12, "bold"),
    )

    state: dict[str, int | None] = {"start_x": None, "start_y": None, "rect": None}

    def close_cancelled(_event: object | None = None) -> None:
        try:
            selector.grab_release()
        except Exception:
            pass
        selector.destroy()
        on_cancelled()

    def on_press(event: tk.Event) -> None:
        state["start_x"] = int(event.x)
        state["start_y"] = int(event.y)
        if state["rect"] is not None:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="#00e5ff",
            width=3,
            fill="#00e5ff",
            stipple="gray25",
        )

    def on_drag(event: tk.Event) -> None:
        if state["rect"] is None or state["start_x"] is None or state["start_y"] is None:
            return
        x = min(max(int(event.x), 0), width)
        y = min(max(int(event.y), 0), height)
        canvas.coords(state["rect"], state["start_x"], state["start_y"], x, y)

    def on_release(event: tk.Event) -> None:
        if state["start_x"] is None or state["start_y"] is None:
            close_cancelled()
            return
        end_x = min(max(int(event.x), 0), width)
        end_y = min(max(int(event.y), 0), height)
        x1, x2 = sorted((state["start_x"], end_x))
        y1, y2 = sorted((state["start_y"], end_y))
        if x2 - x1 < 20 or y2 - y1 < 20:
            close_cancelled()
            return

        try:
            selector.grab_release()
        except Exception:
            pass
        selector.destroy()
        on_selected(
            (
                clamp_ratio(x1 / width),
                clamp_ratio(y1 / height),
                clamp_ratio(x2 / width),
                clamp_ratio(y2 / height),
            )
        )

    selector.bind("<Escape>", close_cancelled)
    selector.bind("<Button-3>", close_cancelled)
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)


def normalize_ocr_text(text: str) -> str:
    text = text.replace("\r", "\n")
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = line.strip("|[]{}~`")
        line = re.sub(r"^[A-Za-z]\s*[_=~`|\\/\-]+\s*", "", line)
        line = re.sub(r"\s+[=_~`|\\/-]+\s*[A-Za-z0-9]{0,4}\.?$", "", line)
        line = re.sub(r"\b(Skip|Auto|Backward|Forward|Close)\b.*$", "", line, flags=re.I).strip()
        if line:
            lines.append(line)
    text = " ".join(lines)
    text = re.sub(r"^[A-Za-z]\s+(?=[A-Z])", "", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    scale = 2
    image = image.resize((image.width * scale, image.height * scale))
    return image.point(lambda px: 255 if px > 150 else 0)


def translate_with_openai(text: str, target_language: str, model: str, base_url: str, api_key: str) -> str:
    api_key = resolve_api_key(api_key, "OPENAI_API_KEY", "OPENAI_API_KEY_FILE")
    if not api_key:
        return "未设置 OPENAI_API_KEY。OCR 原文：\n" + text

    payload = {
        "model": model,
        "instructions": (
            "You translate visual novel dialogue. Translate into "
            f"{target_language}. Keep character names and line breaks natural. "
            "Return only the translation, without commentary."
        ),
        "input": text,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + "/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return f"翻译请求失败：HTTP {exc.code}\n{detail[:600]}"
    except Exception as exc:
        return f"翻译请求失败：{exc}"

    if body.get("output_text"):
        return str(body["output_text"]).strip()

    chunks: list[str] = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return "\n".join(chunks).strip() or "翻译返回为空。"


def read_text_with_openai(image: Image.Image, model: str, base_url: str, api_key: str) -> str:
    api_key = resolve_api_key(api_key, "OPENAI_API_KEY", "OPENAI_API_KEY_FILE")
    if not api_key:
        return ""

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Read only the English dialogue text from this visual novel screenshot crop. "
                            "Return the extracted text only, with natural line breaks. "
                            "If there is no readable dialogue, return an empty string."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_data}",
                    },
                ],
            }
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + "/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""

    if body.get("output_text"):
        return normalize_ocr_text(str(body["output_text"]))

    chunks: list[str] = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return normalize_ocr_text("\n".join(chunks).strip())


def translate_with_libretranslate(text: str, target_language: str, endpoint: str) -> str:
    payload = {
        "q": text,
        "source": "en",
        "target": target_language,
        "format": "text",
    }
    data = json.dumps(payload).encode("utf-8")
    url = endpoint.rstrip("/") + "/translate"
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return f"LibreTranslate 请求失败：HTTP {exc.code}\n{detail[:600]}"
    except Exception as exc:
        return f"LibreTranslate 请求失败：{exc}\n请确认本地服务已启动：http://127.0.0.1:5000"

    return str(body.get("translatedText", "")).strip() or "LibreTranslate 返回为空。"


def read_secret_from_file(path: str) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            return file.read().strip()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def resolve_api_key(explicit_value: str, env_var: str, legacy_file_env_var: str = "") -> str:
    value = explicit_value.strip()
    if value:
        if os.path.isfile(value):
            file_secret = read_secret_from_file(value)
            if file_secret:
                return file_secret
        return value

    env_value = os.environ.get(env_var, "").strip()
    if env_value:
        return env_value

    if legacy_file_env_var:
        return read_secret_from_file(os.environ.get(legacy_file_env_var, "").strip())

    return ""


def translate_with_argos(text: str, target_language: str) -> str:
    try:
        import argostranslate.translate
    except Exception as exc:
        return f"Argos Translate 不可用：{exc}\n请用 start_translator_local.ps1 启动，或重新运行 install_local_stack.ps1。"

    target = "zh" if target_language in {"zh", "zh-Hans", "zh-CN"} else target_language
    try:
        return argostranslate.translate.translate(text, "en", target).strip()
    except Exception as exc:
        return f"Argos Translate 翻译失败：{exc}"


def build_context_prompt(text: str, context_lines: list[str], work_context: str = "") -> str:
    sections: list[str] = []
    if work_context:
        sections.append(
            "Work/wiki context for translation consistency. Use it only when relevant and do not summarize it:\n"
            f"{work_context}"
        )
    if context_lines:
        context = "\n".join(f"- {line}" for line in context_lines[-8:])
        sections.append(f"Recent previous dialogue, for context only:\n{context}")
    sections.append("Translate only this current dialogue:\n" + text)
    return "\n\n".join(sections)


def translate_with_chat_completions(
    provider_name: str,
    text: str,
    context_lines: list[str],
    target_language: str,
    model: str,
    base_url: str,
    api_key: str,
    api_key_env: str,
    legacy_file_env_var: str,
    work_context: str = "",
) -> str:
    api_key = resolve_api_key(api_key, api_key_env, legacy_file_env_var)
    if not api_key:
        return f"{provider_name} API key is missing. OCR text:\n{text}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You translate English visual novel dialogue into "
                    f"{target_language}. Preserve speaker names when present. "
                    "Ignore OCR artifacts, random symbols, and garbled UI fragments. "
                    "Use wiki/work context and recent dialogue only to resolve setting, character names, pronouns, tone, and omitted subjects. "
                    "If the line contains speaker labels or character names, keep each character's translated name consistent across the whole work. "
                    "Do not translate the same character name in multiple different ways unless the source uses a distinct title, nickname, honorific, or relationship term. "
                    "Return one stable natural translation of the current dialogue only. "
                    "Do not include alternatives, explanations, wiki notes, or OCR text."
                ),
            },
            {"role": "user", "content": build_context_prompt(text, context_lines, work_context)},
        ],
        "stream": False,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    url = base_url.rstrip("/") + "/chat/completions"
    req = request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return f"{provider_name} request failed: HTTP {exc.code}\n{detail[:600]}"
    except Exception as exc:
        return f"{provider_name} request failed: {exc}"

    try:
        return str(body["choices"][0]["message"]["content"]).strip()
    except Exception:
        return f"{provider_name} returned an unexpected response:\n" + json.dumps(body, ensure_ascii=False)[:800]


def translate_with_deepseek(
    text: str,
    context_lines: list[str],
    target_language: str,
    model: str,
    base_url: str,
    api_key: str,
    work_context: str = "",
) -> str:
    return translate_with_chat_completions(
        "DeepSeek",
        text,
        context_lines,
        target_language,
        model,
        base_url,
        api_key,
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY_FILE",
        work_context,
    )


def translate_with_grok(
    text: str,
    context_lines: list[str],
    target_language: str,
    model: str,
    base_url: str,
    api_key: str,
    work_context: str = "",
) -> str:
    return translate_with_chat_completions(
        "Grok",
        text,
        context_lines,
        target_language,
        model,
        base_url,
        api_key,
        "XAI_API_KEY",
        "GROK_API_KEY_FILE",
        work_context,
    )


def translate_text(text: str, args: "TranslatorSettings", context_lines: list[str] | None = None, work_context: str = "") -> str:
    context_lines = context_lines or []
    if args.translator == "argos":
        return translate_with_argos(text, args.libre_target)
    if args.translator == "libretranslate":
        return translate_with_libretranslate(text, args.libre_target, args.libre_url)
    if args.translator == "deepseek":
        return translate_with_deepseek(
            text,
            context_lines,
            args.target_language,
            args.model,
            args.api_url or args.deepseek_url,
            args.api_key or args.deepseek_api_key,
            work_context,
        )
    if args.translator == "grok":
        return translate_with_grok(
            text,
            context_lines,
            args.target_language,
            args.model,
            args.api_url or args.grok_url,
            args.api_key or args.grok_api_key,
            work_context,
        )
    return translate_with_openai(
        text,
        args.target_language,
        args.model,
        args.api_url or API_PROVIDER_CONFIGS["openai"]["base_url"],
        args.api_key,
    )


@dataclass
class TranslatorSettings:
    translator: str
    target_language: str
    model: str
    libre_url: str
    libre_target: str
    deepseek_model: str
    deepseek_url: str
    deepseek_api_key: str
    grok_model: str
    grok_url: str
    grok_api_key: str
    api_url: str
    api_key: str
    context_lines: int
    stable_reads: int
    output_layout: str
    font_family: str
    font_size: int
    left: float
    top: float
    right: float
    bottom: float


def translate_image_with_openai(
    image: Image.Image,
    target_language: str,
    model: str,
    base_url: str,
    api_key: str,
) -> tuple[str, str]:
    api_key = resolve_api_key(api_key, "OPENAI_API_KEY", "OPENAI_API_KEY_FILE")
    if not api_key:
        return "", "未设置 OPENAI_API_KEY，且未检测到本地 Tesseract OCR。"

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_data = base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Read the English dialogue text in this visual novel screenshot crop, "
                            f"then translate it into {target_language}. Return only the translation. "
                            "If there is no readable dialogue, return an empty string."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_data}",
                    },
                ],
            }
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        base_url.rstrip("/") + "/responses",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return "", f"图像翻译请求失败：HTTP {exc.code}\n{detail[:600]}"
    except Exception as exc:
        return "", f"图像翻译请求失败：{exc}"

    if body.get("output_text"):
        return "", str(body["output_text"]).strip()

    chunks: list[str] = []
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                chunks.append(str(content["text"]))
    return "", "\n".join(chunks).strip()


def load_local_settings() -> dict[str, object]:
    path = local_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save_local_settings(settings: dict[str, object]) -> None:
    path = local_config_path()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=2)


def append_vocabulary_entry(entry: dict[str, object]) -> None:
    path = ensure_vocabulary_file()
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_vocabulary_entries() -> list[dict[str, object]]:
    path = ensure_vocabulary_file()
    if not os.path.exists(path):
        return []
    entries: list[dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                entries.append(item)
    return entries


class TranslatorApp:
    def _app_title(self) -> str:
        return self._tr("app_title")

    def _tr(self, key: str, **kwargs: object) -> str:
        bundle = UI_STRINGS.get(self.ui_language, UI_STRINGS["en"])
        text = bundle.get(key, UI_STRINGS["en"].get(key, key))
        return text.format(**kwargs) if kwargs else text

    def _language_display_name(self, value: str) -> str:
        if value == "auto":
            return self._tr("label_system_language_auto")
        names = {"en": "English", "zh-CN": "简体中文"}
        return names.get(value, value)

    def _panel_language_label(self, value: str) -> str:
        return OUTPUT_LANGUAGE_LABELS.get(value, {}).get(self.ui_language, value)

    def _apply_theme(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg=UI_COLORS["bg"])
        style.configure(".", background=UI_COLORS["bg"], foreground=UI_COLORS["ink"])
        style.configure(
            "Root.TFrame",
            background=UI_COLORS["bg"],
        )
        style.configure(
            "Card.TFrame",
            background=UI_COLORS["panel"],
            relief="flat",
        )
        style.configure(
            "CardAlt.TFrame",
            background=UI_COLORS["panel_alt"],
        )
        style.configure(
            "Section.TLabelframe",
            background=UI_COLORS["panel"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["ink"],
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "ReadPane.TLabelframe",
            background=UI_COLORS["panel"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "ReadPane.TLabelframe.Label",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["teal"],
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "HeroTitle.TLabel",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["ink"],
            font=("Microsoft YaHei UI", 12, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["muted"],
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background=UI_COLORS["panel_alt"],
            foreground=UI_COLORS["ink"],
            font=("Microsoft YaHei UI", 9, "bold"),
            padding=(12, 8),
        )
        style.configure(
            "Accent.TButton",
            background=UI_COLORS["accent"],
            foreground="#FFFFFF",
            bordercolor=UI_COLORS["accent"],
            focusthickness=0,
            padding=(12, 7),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#AF6B32"), ("pressed", "#9D5F2B")],
            foreground=[("disabled", "#EEE6DD")],
        )
        style.configure(
            "Secondary.TButton",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["ink"],
            bordercolor=UI_COLORS["panel_edge"],
            focusthickness=0,
            padding=(10, 7),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#F6F0E7"), ("pressed", "#EBDDCA")],
        )
        style.configure(
            "Danger.TButton",
            background=UI_COLORS["danger"],
            foreground="#FFFFFF",
            bordercolor=UI_COLORS["danger"],
            focusthickness=0,
            padding=(10, 7),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#95503C"), ("pressed", "#814432")],
        )
        style.configure(
            "TEntry",
            fieldbackground="#FFFDFC",
            foreground=UI_COLORS["ink"],
            bordercolor=UI_COLORS["panel_edge"],
            lightcolor=UI_COLORS["panel_edge"],
            darkcolor=UI_COLORS["panel_edge"],
            insertcolor=UI_COLORS["ink"],
            padding=5,
        )
        style.configure(
            "TCombobox",
            fieldbackground="#FFFDFC",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["ink"],
            bordercolor=UI_COLORS["panel_edge"],
            lightcolor=UI_COLORS["panel_edge"],
            darkcolor=UI_COLORS["panel_edge"],
            arrowsize=14,
            padding=4,
        )
        style.configure(
            "TSpinbox",
            fieldbackground="#FFFDFC",
            foreground=UI_COLORS["ink"],
            arrowsize=14,
        )
        style.configure(
            "TCheckbutton",
            background=UI_COLORS["panel"],
            foreground=UI_COLORS["ink"],
        )
        style.map("TCheckbutton", background=[("active", UI_COLORS["panel"])])

    def _on_ui_language_changed(self) -> None:
        selected = self.ui_language_var.get().strip() or DEFAULT_UI_LANGUAGE
        self.ui_language = detect_system_language() if selected == "auto" else selected
        self._rebuild_ui_language()
        self.save_settings()

    def _rebuild_ui_language(self) -> None:
        if self.provider_config_window is not None and self.provider_config_window.winfo_exists():
            self.provider_config_window.destroy()
            self.provider_config_window = None
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.main_controls = None
        self.crop_frame = None
        self.output_frame = None
        self.left_output_frame = None
        self.right_output_frame = None
        self.reading_splitter = None
        self.left_output = None
        self.right_output = None
        self.window_combo = None
        self.model_combo = None
        self.status_text.set(self._tr("status_ready") if not self.status_text.get() else self.status_text.get())
        self.root.title(f"{self._app_title()} [{self.title_status_text}]")
        self._build_ui()
        self.refresh_window_list()
        self._sync_api_provider_fields()
        self._refresh_outputs_for_current_text()

    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.ui_language_var = tk.StringVar(value=args.ui_language)
        self.ui_language = detect_system_language() if args.ui_language == "auto" else args.ui_language
        self.root.title(self._app_title())
        self.root.geometry("860x780")
        self.root.attributes("-topmost", True)
        self._apply_theme()

        self.running = False
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.last_ocr_text = ""
        self.translation_cache: dict[str, str] = {}
        self.status_text = tk.StringVar(value=self._tr("status_ready"))
        self.title_status_text = self._tr("title_ready")
        self.config_path = local_config_path()

        self.title_var = tk.StringVar(value=args.title)
        self.left_language_var = tk.StringVar(value=args.left_language)
        self.right_language_var = tk.StringVar(value=args.right_language)
        self.openai_model_var = tk.StringVar(value=args.openai_model)
        self.openai_url_var = tk.StringVar(value=args.openai_url)
        self.openai_api_key_var = tk.StringVar(value=args.openai_api_key)
        self.model_var = tk.StringVar(value=args.model)
        self.ocr_engine_var = tk.StringVar(value=args.ocr_engine)
        self.translator_var = tk.StringVar(value=args.translator)
        self.libre_url_var = tk.StringVar(value=args.libre_url)
        self.libre_target_var = tk.StringVar(value=args.libre_target)
        self.deepseek_model_var = tk.StringVar(value=args.deepseek_model)
        self.deepseek_url_var = tk.StringVar(value=args.deepseek_url)
        self.deepseek_api_key_var = tk.StringVar(value=args.deepseek_api_key)
        self.grok_model_var = tk.StringVar(value=args.grok_model)
        self.grok_url_var = tk.StringVar(value=args.grok_url)
        self.grok_api_key_var = tk.StringVar(value=args.grok_api_key)
        initial_api_url = args.api_url or self._default_api_url(args.translator)
        initial_api_key = args.api_key or self._default_api_key(args.translator)
        self.api_url_var = tk.StringVar(value=initial_api_url)
        self.api_key_var = tk.StringVar(value=initial_api_key)
        self.context_lines_var = tk.IntVar(value=args.context_lines)
        self.stable_reads_var = tk.IntVar(value=args.stable_reads)
        self.interval_var = tk.IntVar(value=args.interval_ms)
        self.output_layout_var = tk.StringVar(value=args.output_layout)
        self.output_font_family_var = tk.StringVar(value=args.font_family)
        self.output_font_size_var = tk.IntVar(value=args.font_size)
        self.left_var = tk.DoubleVar(value=args.left)
        self.top_var = tk.DoubleVar(value=args.top)
        self.right_var = tk.DoubleVar(value=args.right)
        self.bottom_var = tk.DoubleVar(value=args.bottom)
        self.pending_ocr_text = ""
        self.pending_ocr_count = 0
        self.last_translated_ocr_text = ""
        self.last_displayed_left_text = ""
        self.last_displayed_right_text = ""
        self.lock_current_line_var = tk.BooleanVar(value=args.lock_current_line)
        self.recent_source_lines: list[str] = []
        self.window_choice_var = tk.StringVar(value="")
        self.window_choices: dict[str, WindowInfo] = {}
        self.work_context_cache: dict[str, str] = {}
        self.current_work_context = ""
        self.current_work_context_key = ""
        self.current_provider = self.translator_var.get().strip()
        self.window_combo: ttk.Combobox | None = None
        self.model_combo: ttk.Combobox | None = None
        self.provider_config_window: tk.Toplevel | None = None
        self.main_controls: ttk.Frame | None = None
        self.crop_frame: ttk.LabelFrame | None = None
        self.status_label: ttk.Label | None = None
        self.reading_shell: ttk.Frame | None = None
        self.reading_header: ttk.Frame | None = None
        self.reading_splitter: tk.PanedWindow | None = None
        self.action_bar: ttk.Frame | None = None
        self.utility_bar: ttk.Frame | None = None
        self.controls_card: ttk.Frame | None = None
        self.advanced_toggle_button: ttk.Button | None = None
        self.advanced_frame: ttk.LabelFrame | None = None
        self.advanced_visible = False
        self.output_font = tkfont.Font(family=self.output_font_family_var.get(), size=self.output_font_size_var.get())
        self.output_frame: ttk.Frame | None = None
        self.left_output_frame: ttk.LabelFrame | None = None
        self.right_output_frame: ttk.LabelFrame | None = None
        self.left_output: tk.Text | None = None
        self.right_output: tk.Text | None = None

        self._build_ui()
        if self.current_provider in API_PROVIDER_CONFIGS:
            self._apply_provider_to_ui(self.current_provider)
        self.refresh_window_list()
        self._sync_api_provider_fields()
        self.translator_var.trace_add("write", lambda *_args: self._on_provider_changed())
        self.api_url_var.trace_add("write", lambda *_args: self._on_api_url_changed())
        self.left_language_var.trace_add("write", lambda *_args: self._refresh_outputs_for_current_text())
        self.right_language_var.trace_add("write", lambda *_args: self._refresh_outputs_for_current_text())
        self.output_layout_var.trace_add("write", lambda *_args: self._rebuild_output_layout())
        self.output_font_family_var.trace_add("write", lambda *_args: self._apply_output_font())
        self.output_font_size_var.trace_add("write", lambda *_args: self._apply_output_font())
        self.ui_language_var.trace_add("write", lambda *_args: self._on_ui_language_changed())

    def _toggle_advanced_panel(self) -> None:
        self.advanced_visible = not self.advanced_visible
        if self.advanced_frame is None:
            return
        if self.advanced_visible:
            self.advanced_frame.pack(fill="x", pady=(10, 0))
        else:
            self.advanced_frame.pack_forget()
        if self.advanced_toggle_button is not None:
            self.advanced_toggle_button.configure(
                text=self._tr("button_hide_advanced") if self.advanced_visible else self._tr("button_show_advanced")
            )

    def _build_ui(self) -> None:
        root = self.root
        root.configure(bg=UI_COLORS["bg"])
        shell = ttk.Frame(root, padding=12, style="Root.TFrame")
        shell.pack(fill="both", expand=True)

        controls = ttk.Frame(shell, padding=12, style="Card.TFrame")
        self.main_controls = controls
        self.controls_card = controls
        controls.pack(fill="x", pady=(0, 10))

        top_bar = ttk.Frame(controls, style="Card.TFrame")
        top_bar.pack(fill="x", pady=(0, 10))
        ttk.Label(top_bar, text=self._tr("label_window_title")).pack(side="left")
        ttk.Entry(top_bar, textvariable=self.title_var, width=28).pack(side="left", padx=(8, 10))
        ttk.Button(top_bar, text=self._tr("button_refresh_windows"), command=self.refresh_window_list, style="Secondary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(top_bar, text=self._tr("button_place_beside"), command=self.place_beside_game, style="Secondary.TButton").pack(side="left")

        action_bar = ttk.Frame(controls, style="Card.TFrame")
        self.action_bar = action_bar
        action_bar.pack(fill="x", pady=(0, 10))
        ttk.Button(action_bar, text=self._tr("button_start"), command=self.start, style="Accent.TButton").pack(side="left")
        ttk.Button(action_bar, text=self._tr("button_retranslate"), command=self.retranslate_current_text, style="Secondary.TButton").pack(side="left", padx=(8, 8))
        ttk.Button(action_bar, text=self._tr("button_stop"), command=self.stop, style="Danger.TButton").pack(side="left")
        ttk.Separator(action_bar, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Button(action_bar, text=self._tr("button_collect_selection"), command=self.collect_selection, style="Secondary.TButton").pack(side="left")
        ttk.Button(action_bar, text=self._tr("button_collect_current"), command=self.collect_current_pair, style="Secondary.TButton").pack(side="left", padx=(8, 0))
        self.advanced_toggle_button = ttk.Button(
            action_bar,
            text=self._tr("button_show_advanced"),
            command=self._toggle_advanced_panel,
            style="Secondary.TButton",
        )
        self.advanced_toggle_button.pack(side="right")

        quick_row = ttk.Frame(controls, style="Card.TFrame")
        quick_row.pack(fill="x")

        ttk.Label(quick_row, text=self._tr("label_left_output")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            quick_row,
            textvariable=self.left_language_var,
            values=OUTPUT_LANGUAGE_OPTIONS,
            width=16,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(8, 14))
        ttk.Label(quick_row, text=self._tr("label_right_output")).grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            quick_row,
            textvariable=self.right_language_var,
            values=OUTPUT_LANGUAGE_OPTIONS,
            width=16,
            state="readonly",
        ).grid(row=0, column=3, sticky="ew", padx=(8, 14))
        ttk.Label(quick_row, text=self._tr("label_layout")).grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            quick_row,
            textvariable=self.output_layout_var,
            values=OUTPUT_LAYOUT_OPTIONS,
            width=10,
            state="readonly",
        ).grid(row=0, column=5, sticky="w", padx=(8, 14))
        ttk.Label(quick_row, text=self._tr("label_model")).grid(row=0, column=6, sticky="w")
        self.model_combo = ttk.Combobox(quick_row, textvariable=self.model_var, width=18)
        self.model_combo.grid(row=0, column=7, sticky="ew", padx=(8, 0))

        meta_row = ttk.Frame(controls, style="Card.TFrame")
        meta_row.pack(fill="x", pady=(10, 0))
        ttk.Label(meta_row, text=self._tr("label_window_list")).grid(row=0, column=0, sticky="w")
        self.window_combo = ttk.Combobox(
            meta_row,
            textvariable=self.window_choice_var,
            values=(),
            width=38,
            state="readonly",
        )
        self.window_combo.grid(row=0, column=1, sticky="ew", padx=(8, 14))
        self.window_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_window_selected())
        ttk.Label(meta_row, text=self._tr("label_translator")).grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            meta_row,
            textvariable=self.translator_var,
            values=("argos", "deepseek", "grok", "libretranslate", "openai"),
            width=14,
            state="readonly",
        ).grid(row=0, column=3, sticky="w", padx=(8, 14))
        ttk.Label(meta_row, text=self._tr("label_ocr")).grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            meta_row,
            textvariable=self.ocr_engine_var,
            values=("auto", "openai-vision", "tesseract"),
            width=14,
            state="readonly",
        ).grid(row=0, column=5, sticky="w", padx=(8, 0))

        utility_row = ttk.Frame(controls, style="Card.TFrame")
        utility_row.pack(fill="x", pady=(10, 0))
        ttk.Button(utility_row, text=self._tr("button_provider_configs"), command=self.open_provider_config_window, style="Secondary.TButton").pack(side="left")
        ttk.Button(utility_row, text=self._tr("button_vocabulary"), command=self.open_vocabulary_window, style="Secondary.TButton").pack(side="left", padx=(8, 0))
        ttk.Checkbutton(utility_row, text=self._tr("check_lock_current_line"), variable=self.lock_current_line_var).pack(side="right")
        ttk.Label(utility_row, text=self._tr("label_system_language")).pack(side="right", padx=(0, 8))
        ttk.Combobox(
            utility_row,
            textvariable=self.ui_language_var,
            values=UI_LANGUAGE_OPTIONS,
            width=10,
            state="readonly",
        ).pack(side="right", padx=(0, 14))
        ttk.Label(utility_row, text=self._tr("label_font_size")).pack(side="right", padx=(0, 8))
        ttk.Spinbox(utility_row, from_=8, to=40, increment=1, textvariable=self.output_font_size_var, width=5).pack(side="right", padx=(0, 14))
        ttk.Label(utility_row, text=self._tr("label_font")).pack(side="right", padx=(0, 8))
        ttk.Entry(utility_row, textvariable=self.output_font_family_var, width=18).pack(side="right", padx=(0, 14))

        quick_row.columnconfigure(1, weight=1)
        quick_row.columnconfigure(3, weight=1)
        quick_row.columnconfigure(7, weight=1)
        meta_row.columnconfigure(1, weight=1)

        advanced = ttk.LabelFrame(controls, text=self._tr("frame_subtitle_crop_area"), padding=10, style="Section.TLabelframe")
        self.advanced_frame = advanced

        ttk.Label(advanced, text=self._tr("label_interval_ms")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(advanced, from_=500, to=10000, increment=250, textvariable=self.interval_var, width=10).grid(
            row=0, column=1, sticky="w", padx=(8, 16)
        )
        ttk.Label(advanced, text=self._tr("label_context")).grid(row=0, column=2, sticky="w")
        ttk.Spinbox(advanced, from_=0, to=12, increment=1, textvariable=self.context_lines_var, width=10).grid(
            row=0, column=3, sticky="w", padx=(8, 16)
        )
        ttk.Label(advanced, text=self._tr("label_stable_reads")).grid(row=0, column=4, sticky="w")
        ttk.Spinbox(advanced, from_=1, to=5, increment=1, textvariable=self.stable_reads_var, width=10).grid(
            row=0, column=5, sticky="w", padx=(8, 0)
        )

        reading_shell = ttk.Frame(shell, padding=12, style="Card.TFrame")
        self.reading_shell = reading_shell
        reading_shell.pack(fill="both", expand=True, pady=(6, 10))

        reading_header = ttk.Frame(reading_shell, style="Card.TFrame")
        self.reading_header = reading_header
        reading_header.pack(fill="x", pady=(0, 10))
        ttk.Label(reading_header, text=self._tr("reading_stage_title"), style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            reading_header,
            text=self._tr("reading_stage_subtitle"),
            style="Muted.TLabel",
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        self.output_frame = ttk.Frame(reading_shell, style="Card.TFrame")
        self.output_frame.pack(fill="both", expand=True)
        self._build_output_layout()

        self.crop_frame = advanced
        ttk.Label(advanced, text=self._tr("label_api_url")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(advanced, textvariable=self.api_url_var, width=32).grid(row=1, column=1, sticky="ew", padx=(8, 16), pady=(8, 0))
        ttk.Label(advanced, text=self._tr("label_api_key")).grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(advanced, textvariable=self.api_key_var, width=20).grid(row=1, column=3, sticky="ew", padx=(8, 16), pady=(8, 0))

        ttk.Label(advanced, text=self._tr("label_libre_url")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(advanced, textvariable=self.libre_url_var, width=32).grid(row=2, column=1, sticky="ew", padx=(8, 16), pady=(8, 0))
        ttk.Label(advanced, text=self._tr("label_libre_target")).grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(advanced, textvariable=self.libre_target_var, width=12).grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(8, 0))

        ttk.Button(advanced, text=self._tr("button_select_area"), command=self.select_capture_area, style="Secondary.TButton").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(10, 6)
        )
        for index, (label, var) in enumerate(
            [
                (self._tr("crop_left"), self.left_var),
                (self._tr("crop_top"), self.top_var),
                (self._tr("crop_right"), self.right_var),
                (self._tr("crop_bottom"), self.bottom_var),
            ]
        ):
            ttk.Label(advanced, text=label).grid(row=4, column=index * 2, sticky="e")
            ttk.Spinbox(advanced, from_=0.0, to=1.0, increment=0.01, textvariable=var, width=7).grid(
                row=4, column=index * 2 + 1, padx=(3, 10)
            )

        status = ttk.Label(shell, textvariable=self.status_text, anchor="w", style="Status.TLabel")
        self.status_label = status
        status.pack(fill="x")
        advanced.columnconfigure(1, weight=1)
        advanced.columnconfigure(3, weight=1)

    def start(self) -> None:
        if self.running:
            return
        self.save_settings()
        self.running = True
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        self._set_status(self._tr("status_running"), self._tr("title_running"))

    def stop(self) -> None:
        self.running = False
        self.stop_event.set()
        self._set_status(self._tr("status_stopped"), self._tr("title_stopped"))

    def refresh_window_list(self) -> None:
        windows = list_capture_windows()
        self.window_choices = {f"{window.title}  [{window.hwnd}]": window for window in windows}
        values = tuple(self.window_choices.keys())
        if self.window_combo is not None:
            self.window_combo.configure(values=values)
        if values and not self.window_choice_var.get():
            self.window_choice_var.set(values[0])
            self._on_window_selected()

    def _on_window_selected(self) -> None:
        selected = self.window_choices.get(self.window_choice_var.get())
        if selected:
            self.title_var.set(selected.title)
            self.current_work_context = ""
            self.current_work_context_key = ""

    def place_beside_game(self) -> None:
        window = self.window_choices.get(self.window_choice_var.get()) or find_window(self.title_var.get())
        if not window:
            messagebox.showwarning(
                self._tr("message_window_not_found_title"),
                self._tr("message_window_not_found_body"),
            )
            return
        left, top, right, bottom = window.rect
        width = 580
        height = min(max(bottom - top, 520), 780)
        self.root.geometry(f"{width}x{height}+{right + 12}+{top}")
        self.root.attributes("-topmost", True)
        try:
            win32gui.SetWindowPos(window.hwnd, None, left, top, right - left, bottom - top, win32con.SWP_SHOWWINDOW)
        except Exception:
            pass

    def select_capture_area(self) -> None:
        window = self.window_choices.get(self.window_choice_var.get()) or find_window(self.title_var.get())
        if not window:
            messagebox.showwarning(
                self._tr("message_window_not_found_title"),
                self._tr("message_select_area_missing_window"),
            )
            return
        self._set_status(self._tr("status_selecting_area"), self._tr("title_selecting_area"))

        def apply_region(region: tuple[float, float, float, float]) -> None:
            left, top, right, bottom = region
            self.left_var.set(round(left, 3))
            self.top_var.set(round(top, 3))
            self.right_var.set(round(right, 3))
            self.bottom_var.set(round(bottom, 3))
            self._set_status(self._tr("status_area_updated"), self._tr("title_area_updated"))

        def cancel_region() -> None:
            self._set_status(self._tr("status_area_cancelled"), self._tr("title_area_cancelled"))

        select_region_for_window(self.root, window, apply_region, cancel_region)

    def _default_api_url(self, provider: str) -> str:
        return str(API_PROVIDER_CONFIGS.get(provider, {}).get("base_url", ""))

    def _default_api_key(self, provider: str) -> str:
        return ""

    def _provider_state(self, provider: str) -> tuple[tk.StringVar, tk.StringVar, tk.StringVar]:
        if provider == "deepseek":
            return self.deepseek_model_var, self.deepseek_url_var, self.deepseek_api_key_var
        if provider == "grok":
            return self.grok_model_var, self.grok_url_var, self.grok_api_key_var
        return self.openai_model_var, self.openai_url_var, self.openai_api_key_var

    def _capture_current_provider_settings(self) -> None:
        provider = self.current_provider
        if provider not in API_PROVIDER_CONFIGS:
            return
        model_var, url_var, key_var = self._provider_state(provider)
        model_var.set(self.model_var.get().strip())
        url_var.set(self.api_url_var.get().strip())
        key_var.set(self.api_key_var.get().strip())

    def _apply_provider_to_ui(self, provider: str) -> None:
        if provider not in API_PROVIDER_CONFIGS:
            return
        model_var, url_var, key_var = self._provider_state(provider)
        self.current_provider = provider
        self.model_var.set(model_var.get().strip() or models_for_provider(provider)[0])
        self.api_url_var.set(url_var.get().strip() or self._default_api_url(provider))
        self.api_key_var.set(key_var.get().strip())

    def use_provider_config(self, provider: str) -> None:
        self._capture_current_provider_settings()
        self.translator_var.set(provider)
        self._apply_provider_to_ui(provider)
        self._sync_api_provider_fields()

    def open_provider_config_window(self) -> None:
        if self.provider_config_window is not None and self.provider_config_window.winfo_exists():
            self.provider_config_window.lift()
            self.provider_config_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title(self._tr("dialog_provider_configs"))
        window.geometry("860x220")
        window.transient(self.root)
        self.provider_config_window = window

        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)

        headers = (
            self._tr("header_provider"),
            self._tr("label_model"),
            self._tr("label_api_url"),
            self._tr("label_api_key"),
            self._tr("header_use"),
        )
        for col, header in enumerate(headers):
            ttk.Label(frame, text=header).grid(row=0, column=col, sticky="w", padx=4, pady=(0, 6))

        provider_rows = [
            ("openai", "OpenAI"),
            ("deepseek", "DeepSeek"),
            ("grok", "Grok"),
        ]
        for row, (provider_key, provider_label) in enumerate(provider_rows, start=1):
            model_var, url_var, key_var = self._provider_state(provider_key)
            ttk.Label(frame, text=provider_label).grid(row=row, column=0, sticky="w", padx=4, pady=4)
            ttk.Entry(frame, textvariable=model_var, width=18).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
            ttk.Entry(frame, textvariable=url_var, width=34).grid(row=row, column=2, sticky="ew", padx=4, pady=4)
            ttk.Entry(frame, textvariable=key_var, width=28).grid(row=row, column=3, sticky="ew", padx=4, pady=4)
            ttk.Button(frame, text=self._tr("button_use"), command=lambda p=provider_key: self.use_provider_config(p)).grid(
                row=row, column=4, sticky="w", padx=4, pady=4
            )

        ttk.Button(frame, text=self._tr("button_save_configs"), command=self.save_settings).grid(row=4, column=3, sticky="e", padx=4, pady=(10, 0))
        ttk.Button(frame, text=self._tr("button_close"), command=window.destroy).grid(row=4, column=4, sticky="w", padx=4, pady=(10, 0))

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.columnconfigure(3, weight=1)
        window.protocol("WM_DELETE_WINDOW", window.destroy)

    def save_settings(self) -> None:
        self._capture_current_provider_settings()
        settings = self._settings()
        payload = {
            "title": self.title_var.get().strip(),
            "target_language": settings.target_language,
            "left_language": self.left_language_var.get().strip(),
            "right_language": self.right_language_var.get().strip(),
            "model": settings.model,
            "openai_model": self.openai_model_var.get().strip(),
            "openai_url": self.openai_url_var.get().strip(),
            "openai_api_key": self.openai_api_key_var.get().strip(),
            "ocr_engine": self.ocr_engine_var.get().strip() or "tesseract",
            "translator": settings.translator,
            "libre_url": settings.libre_url,
            "libre_target": settings.libre_target,
            "deepseek_model": settings.deepseek_model,
            "deepseek_url": settings.deepseek_url,
            "deepseek_api_key": settings.deepseek_api_key,
            "grok_model": settings.grok_model,
            "grok_url": settings.grok_url,
            "grok_api_key": settings.grok_api_key,
            "api_url": settings.api_url,
            "api_key": settings.api_key,
            "context_lines": settings.context_lines,
            "stable_reads": settings.stable_reads,
            "lock_current_line": self.lock_current_line_var.get(),
            "interval_ms": self.interval_var.get(),
            "ui_language": self.ui_language_var.get().strip() or DEFAULT_UI_LANGUAGE,
            "output_layout": settings.output_layout,
            "font_family": settings.font_family,
            "font_size": settings.font_size,
            "left": settings.left,
            "top": settings.top,
            "right": settings.right,
            "bottom": settings.bottom,
        }
        save_local_settings(payload)

    def _on_provider_changed(self) -> None:
        self._capture_current_provider_settings()
        provider = self.translator_var.get().strip()
        if provider in API_PROVIDER_CONFIGS:
            self._apply_provider_to_ui(provider)
        self._sync_api_provider_fields()

    def _on_api_url_changed(self) -> None:
        provider = detect_api_provider(self.api_url_var.get(), self.translator_var.get().strip())
        if provider in API_PROVIDER_CONFIGS and provider != self.translator_var.get():
            self.translator_var.set(provider)
            return
        self._sync_api_provider_fields()

    def _sync_api_provider_fields(self) -> None:
        provider = detect_api_provider(self.api_url_var.get(), self.translator_var.get().strip())
        model_values = models_for_provider(provider)
        if self.model_combo is not None:
            self.model_combo.configure(values=model_values)
            self.model_combo.configure(state="readonly" if model_values else "normal")
        if model_values and self.model_var.get() not in model_values:
            self.model_var.set(model_values[0])

    def _apply_output_font(self) -> None:
        family = self.output_font_family_var.get().strip() or DEFAULT_OUTPUT_FONT_FAMILY
        size = max(self.output_font_size_var.get(), 8)
        self.output_font.configure(family=family, size=size)

    def _set_status(self, text: str, title_hint: str = "") -> None:
        self.status_text.set(text)
        self.title_status_text = title_hint or text
        self.root.title(f"{self._app_title()} [{self.title_status_text}]")

    def _build_output_layout(self) -> None:
        if self.output_frame is None:
            return
        layout = self.output_layout_var.get().strip() or DEFAULT_OUTPUT_LAYOUT
        is_vertical = layout == "vertical"
        left_label = self._panel_language_label(self.left_language_var.get().strip() or DEFAULT_OUTPUT_LEFT_LANGUAGE)
        right_label = self._panel_language_label(self.right_language_var.get().strip() or DEFAULT_OUTPUT_RIGHT_LANGUAGE)
        orient = "vertical" if is_vertical else "horizontal"

        self.reading_splitter = tk.PanedWindow(
            self.output_frame,
            orient=orient,
            sashwidth=8,
            bg=UI_COLORS["panel"],
            bd=0,
            relief="flat",
            opaqueresize=True,
        )
        self.reading_splitter.pack(fill="both", expand=True)

        self.left_output_frame = ttk.LabelFrame(
            self.reading_splitter,
            text=f"{self._tr('panel_top') if is_vertical else self._tr('panel_left')}: {left_label}",
            padding=6,
            style="ReadPane.TLabelframe",
        )
        self.right_output_frame = ttk.LabelFrame(
            self.reading_splitter,
            text=f"{self._tr('panel_bottom') if is_vertical else self._tr('panel_right')}: {right_label}",
            padding=6,
            style="ReadPane.TLabelframe",
        )

        self.reading_splitter.add(self.left_output_frame, stretch="always", minsize=220)
        self.reading_splitter.add(self.right_output_frame, stretch="always", minsize=220)

        self.left_output = tk.Text(
            self.left_output_frame,
            wrap="word",
            font=self.output_font,
            height=11,
            bg="#FFFDFC",
            fg=UI_COLORS["ink"],
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            insertbackground=UI_COLORS["ink"],
            selectbackground=UI_COLORS["accent_soft"],
            highlightthickness=1,
            highlightbackground=UI_COLORS["panel_edge"],
            highlightcolor=UI_COLORS["accent"],
        )
        self.left_output.pack(fill="both", expand=True)
        self.right_output = tk.Text(
            self.right_output_frame,
            wrap="word",
            font=self.output_font,
            height=11,
            bg="#FFFDFC",
            fg=UI_COLORS["ink"],
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            insertbackground=UI_COLORS["ink"],
            selectbackground=UI_COLORS["teal_soft"],
            highlightthickness=1,
            highlightbackground=UI_COLORS["panel_edge"],
            highlightcolor=UI_COLORS["teal"],
        )
        self.right_output.pack(fill="both", expand=True)

        self.left_output.insert(
            "1.0",
            self.last_displayed_left_text
            or self._tr("placeholder_left"),
        )
        self.right_output.insert(
            "1.0",
            self.last_displayed_right_text or self._tr("placeholder_right"),
        )

    def _rebuild_output_layout(self) -> None:
        if self.output_frame is None:
            return
        if self.reading_splitter is not None:
            self.reading_splitter.destroy()
        elif self.left_output_frame is not None:
            self.left_output_frame.destroy()
        elif self.right_output_frame is not None:
            self.right_output_frame.destroy()
        self.reading_splitter = None
        self.left_output = None
        self.right_output = None
        self._build_output_layout()

    def _refresh_outputs_for_current_text(self) -> None:
        self._rebuild_output_layout()
        source_text = self.pending_ocr_text or self.last_translated_ocr_text or self.last_ocr_text
        if source_text:
            self._translate_current_text(source_text, force_refresh=False)

    def _set_left_output(self, text: str) -> None:
        if text == self.last_displayed_left_text or self.left_output is None:
            return
        self.last_displayed_left_text = text
        self.left_output.delete("1.0", "end")
        self.left_output.insert("1.0", text)

    def _set_right_output(self, text: str) -> None:
        if text == self.last_displayed_right_text or self.right_output is None:
            return
        self.last_displayed_right_text = text
        self.right_output.delete("1.0", "end")
        self.right_output.insert("1.0", text)

    def _selected_text(self, widget: tk.Text | None) -> str:
        if widget is None:
            return ""
        try:
            return widget.get("sel.first", "sel.last").strip()
        except tk.TclError:
            return ""

    def collect_selection(self) -> None:
        left_selection = self._selected_text(self.left_output)
        right_selection = self._selected_text(self.right_output)
        source_text = left_selection or self.last_displayed_left_text.strip()
        translation_text = right_selection or self.last_displayed_right_text.strip()

        if not left_selection and not right_selection:
            messagebox.showinfo(self._tr("message_no_selection_title"), self._tr("message_no_selection_body"))
            return

        self.open_collect_dialog(source_text, translation_text)

    def collect_current_pair(self) -> None:
        source_text = self.last_displayed_left_text.strip()
        translation_text = self.last_displayed_right_text.strip()
        if not source_text and not translation_text:
            messagebox.showinfo(self._tr("message_no_current_text_title"), self._tr("message_no_current_text_body"))
            return
        self.open_collect_dialog(source_text, translation_text)

    def open_collect_dialog(self, source_text: str, translation_text: str) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(self._tr("dialog_collect_vocabulary"))
        dialog.geometry("720x420")
        dialog.transient(self.root)

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)

        source_var = tk.StringVar(value=source_text)
        translation_var = tk.StringVar(value=translation_text)
        kind_var = tk.StringVar(value="phrase" if " " in source_text else "word")
        tags_var = tk.StringVar(value="")

        ttk.Label(frame, text=self._tr("label_source")).grid(row=0, column=0, sticky="w")
        source_box = tk.Text(frame, height=5, wrap="word")
        source_box.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(2, 8))
        source_box.insert("1.0", source_var.get())

        ttk.Label(frame, text=self._tr("label_translation")).grid(row=2, column=0, sticky="w")
        translation_box = tk.Text(frame, height=5, wrap="word")
        translation_box.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(2, 8))
        translation_box.insert("1.0", translation_var.get())

        ttk.Label(frame, text=self._tr("label_kind")).grid(row=4, column=0, sticky="w")
        ttk.Combobox(frame, textvariable=kind_var, values=("word", "phrase", "sentence"), width=12, state="readonly").grid(
            row=4, column=1, sticky="w", pady=(0, 8)
        )

        ttk.Label(frame, text=self._tr("label_tags")).grid(row=5, column=0, sticky="w")
        ttk.Entry(frame, textvariable=tags_var, width=32).grid(row=5, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text=self._tr("label_note")).grid(row=6, column=0, sticky="w")
        note_box = tk.Text(frame, height=4, wrap="word")
        note_box.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(2, 8))

        def save_entry() -> None:
            source_value = source_box.get("1.0", "end").strip()
            translation_value = translation_box.get("1.0", "end").strip()
            note_value = note_box.get("1.0", "end").strip()
            if not source_value:
                messagebox.showwarning(self._tr("message_missing_source_title"), self._tr("message_missing_source_body"))
                return
            entry = {
                "source": source_value,
                "translation": translation_value,
                "source_language": self.left_language_var.get().strip(),
                "target_language": self.right_language_var.get().strip(),
                "kind": kind_var.get().strip() or "phrase",
                "tags": [tag.strip() for tag in tags_var.get().split(",") if tag.strip()],
                "note": note_value,
                "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                "window_title": self.title_var.get().strip(),
            }
            append_vocabulary_entry(entry)
            self._set_status(self._tr("status_vocabulary_collected"), self._tr("title_collected"))
            dialog.destroy()

        button_row = ttk.Frame(frame)
        button_row.grid(row=8, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text=self._tr("button_save"), command=save_entry).pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text=self._tr("button_close"), command=dialog.destroy).pack(side="left")

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)
        frame.rowconfigure(7, weight=1)

    def _translate_current_text(self, ocr_text: str, force_refresh: bool = False) -> None:
        if not ocr_text:
            self._set_status(self._tr("status_no_ocr_text"), self._tr("title_idle"))
            return
        if force_refresh:
            self.translation_cache.clear()

        self._set_status(self._tr("status_translating"), self._tr("title_translating"))
        settings = self._settings()
        context = self._translation_context()
        window = self.window_choices.get(self.window_choice_var.get()) or find_window(self.title_var.get())
        work_context = self._work_context_for_window(window, settings) if window else ""
        left_text = self._panel_text(ocr_text, self.left_language_var.get().strip(), settings, context, work_context)
        right_text = self._panel_text(ocr_text, self.right_language_var.get().strip(), settings, context, work_context)
        self.last_ocr_text = ocr_text
        self.last_translated_ocr_text = ocr_text
        self._remember_source_line(ocr_text)
        self._set_left_output(left_text)
        self._set_right_output(right_text)
        self._set_status(self._tr("status_updated"), self._tr("title_ready"))

    def retranslate_current_text(self) -> None:
        source_text = self.pending_ocr_text or self.last_translated_ocr_text or self.last_ocr_text
        self._translate_current_text(source_text, force_refresh=True)

    def open_vocabulary_window(self) -> None:
        window = tk.Toplevel(self.root)
        window.title(self._tr("dialog_vocabulary"))
        window.geometry("900x520")
        window.transient(self.root)

        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)

        columns = ("created_at", "kind", "source", "translation", "tags")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        headings = {
            "created_at": self._tr("column_created"),
            "kind": self._tr("column_kind"),
            "source": self._tr("column_source"),
            "translation": self._tr("column_translation"),
            "tags": self._tr("column_tags"),
        }
        widths = {
            "created_at": 140,
            "kind": 80,
            "source": 240,
            "translation": 260,
            "tags": 140,
        }
        for key in columns:
            tree.heading(key, text=headings[key])
            tree.column(key, width=widths[key], anchor="w")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        details = tk.Text(frame, height=8, wrap="word")
        details.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        entries = load_vocabulary_entries()
        for index, entry in enumerate(entries):
            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    str(entry.get("created_at", "")),
                    str(entry.get("kind", "")),
                    str(entry.get("source", "")),
                    str(entry.get("translation", "")),
                    ", ".join(entry.get("tags", [])) if isinstance(entry.get("tags"), list) else str(entry.get("tags", "")),
                ),
            )

        def on_select(_event: object) -> None:
            selected = tree.selection()
            if not selected:
                return
            entry = entries[int(selected[0])]
            lines = [
                f"{self._tr('label_source')}: {entry.get('source', '')}",
                f"{self._tr('label_translation')}: {entry.get('translation', '')}",
                f"{self._tr('details_source_language')}: {entry.get('source_language', '')}",
                f"{self._tr('details_target_language')}: {entry.get('target_language', '')}",
                f"{self._tr('label_kind')}: {entry.get('kind', '')}",
                f"{self._tr('label_tags')}: {', '.join(entry.get('tags', [])) if isinstance(entry.get('tags'), list) else entry.get('tags', '')}",
                f"{self._tr('details_window')}: {entry.get('window_title', '')}",
                f"{self._tr('column_created')}: {entry.get('created_at', '')}",
                "",
                f"{self._tr('label_note')}: {entry.get('note', '')}",
            ]
            details.delete("1.0", "end")
            details.insert("1.0", "\n".join(lines))

        tree.bind("<<TreeviewSelect>>", on_select)

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

    def _loop(self) -> None:
        with mss.mss() as capture:
            while not self.stop_event.is_set():
                try:
                    window = self.window_choices.get(self.window_choice_var.get()) or find_window(self.title_var.get())
                    if not window:
                        self.root.after(0, self._set_status, self._tr("status_window_not_found"), self._tr("title_window_not_found"))
                        time.sleep(1)
                        continue

                    image = self._capture_subtitle_area(capture, window)
                    ocr_text = self._read_text_from_image(image)
                    if (
                        ocr_text
                        and self.last_translated_ocr_text
                        and ocr_texts_are_similar(ocr_text, self.last_translated_ocr_text)
                    ):
                        self.last_ocr_text = ocr_text
                        self.root.after(0, self._set_status, self._tr("status_same_dialogue"), self._tr("title_idle"))
                    elif ocr_text and ocr_text != self.last_ocr_text:
                        if self.lock_current_line_var.get():
                            self.last_ocr_text = ocr_text
                            self.root.after(0, self._set_status, self._tr("status_locked_new_dialogue"), self._tr("title_locked"))
                            time.sleep(max(self.interval_var.get(), 500) / 1000)
                            continue
                        if not self._ocr_is_stable(ocr_text):
                            self.root.after(0, self._set_status, self._tr("status_waiting_stable_ocr"), self._tr("title_waiting_ocr"))
                            time.sleep(max(self.interval_var.get(), 500) / 1000)
                            continue

                        ocr_text = self.pending_ocr_text
                        self.root.after(0, self._translate_current_text, ocr_text, False)
                    else:
                        self.root.after(0, self._set_status, self._tr("status_no_new_text"), self._tr("title_idle"))
                except Exception as exc:
                    self.root.after(0, self._set_status, self._tr("status_error", error=exc), self._tr("title_error"))

                time.sleep(max(self.interval_var.get(), 500) / 1000)

    def _capture_subtitle_area(self, capture: mss.mss, window: WindowInfo) -> Image.Image:
        screenshot = capture_window_image(window)
        width = screenshot.width
        height = screenshot.height
        crop_left = max(min(int(width * self.left_var.get()), width - 1), 0)
        crop_top = max(min(int(height * self.top_var.get()), height - 1), 0)
        crop_right = max(min(int(width * self.right_var.get()), width), crop_left + 1)
        crop_bottom = max(min(int(height * self.bottom_var.get()), height), crop_top + 1)
        return screenshot.crop((crop_left, crop_top, crop_right, crop_bottom))

    def _ocr(self, image: Image.Image) -> str:
        prepared = preprocess_for_ocr(image)
        config = "--psm 6"
        text = pytesseract.image_to_string(prepared, lang="eng", config=config)
        return normalize_ocr_text(text)

    def _read_text_from_image(self, image: Image.Image) -> str:
        engine = self.ocr_engine_var.get()
        has_tesseract = tesseract_is_available()
        if engine == "tesseract" or (engine == "auto" and has_tesseract):
            return self._ocr(image)
        if engine == "auto" or engine == "openai-vision":
            self.root.after(0, self._set_status, self._tr("status_reading_ocr"), self._tr("title_reading_ocr"))
            return read_text_with_openai(
                image,
                self.model_var.get().strip() or "gpt-4o-mini",
                self.api_url_var.get().strip() or API_PROVIDER_CONFIGS["openai"]["base_url"],
                self.api_key_var.get().strip(),
            )
        return ""

    def _panel_text(
        self,
        ocr_text: str,
        output_language: str,
        settings: TranslatorSettings,
        context: list[str],
        work_context: str,
    ) -> str:
        language = output_language or DEFAULT_OUTPUT_RIGHT_LANGUAGE
        if language == ORIGINAL_OCR_LANGUAGE:
            return ocr_text
        cache_key = self._cache_key(ocr_text, settings, context, work_context, language)
        translation = self.translation_cache.get(cache_key)
        if translation is None:
            panel_settings = TranslatorSettings(
                translator=settings.translator,
                target_language=language,
                model=settings.model,
                libre_url=settings.libre_url,
                libre_target=settings.libre_target,
                deepseek_model=settings.deepseek_model,
                deepseek_url=settings.deepseek_url,
                deepseek_api_key=settings.deepseek_api_key,
                grok_model=settings.grok_model,
                grok_url=settings.grok_url,
                grok_api_key=settings.grok_api_key,
                api_url=settings.api_url,
                api_key=settings.api_key,
                context_lines=settings.context_lines,
                stable_reads=settings.stable_reads,
                output_layout=settings.output_layout,
                font_family=settings.font_family,
                font_size=settings.font_size,
                left=settings.left,
                top=settings.top,
                right=settings.right,
                bottom=settings.bottom,
            )
            translation = translate_text(ocr_text, panel_settings, context, work_context)
            self.translation_cache[cache_key] = translation
        return translation

    def _settings(self) -> TranslatorSettings:
        return TranslatorSettings(
            translator=self.translator_var.get().strip() or "argos",
            target_language=self.right_language_var.get().strip() or DEFAULT_OUTPUT_RIGHT_LANGUAGE,
            model=self.model_var.get().strip() or "gpt-5-mini",
            libre_url=self.libre_url_var.get().strip() or "http://127.0.0.1:5000",
            libre_target=self.libre_target_var.get().strip() or "zh-Hans",
            deepseek_model=self.deepseek_model_var.get().strip() or "deepseek-v4-flash",
            deepseek_url=self.deepseek_url_var.get().strip() or "https://api.deepseek.com",
            deepseek_api_key=self.deepseek_api_key_var.get().strip(),
            grok_model=self.grok_model_var.get().strip() or "grok-4",
            grok_url=self.grok_url_var.get().strip() or "https://api.x.ai/v1",
            grok_api_key=self.grok_api_key_var.get().strip(),
            api_url=self.api_url_var.get().strip(),
            api_key=self.api_key_var.get().strip(),
            context_lines=max(self.context_lines_var.get(), 0),
            stable_reads=max(self.stable_reads_var.get(), 1),
            output_layout=self.output_layout_var.get().strip() or DEFAULT_OUTPUT_LAYOUT,
            font_family=self.output_font_family_var.get().strip() or DEFAULT_OUTPUT_FONT_FAMILY,
            font_size=max(self.output_font_size_var.get(), 8),
            left=self.left_var.get(),
            top=self.top_var.get(),
            right=self.right_var.get(),
            bottom=self.bottom_var.get(),
        )

    def _ocr_is_stable(self, text: str) -> bool:
        if text == self.pending_ocr_text or ocr_texts_are_similar(text, self.pending_ocr_text):
            self.pending_ocr_count += 1
            if ocr_text_quality_score(text) > ocr_text_quality_score(self.pending_ocr_text):
                self.pending_ocr_text = text
        else:
            self.pending_ocr_text = text
            self.pending_ocr_count = 1
        return self.pending_ocr_count >= max(self.stable_reads_var.get(), 1)

    def _translation_context(self) -> list[str]:
        count = max(self.context_lines_var.get(), 0)
        if count <= 0:
            return []
        return self.recent_source_lines[-count:]

    def _work_context_for_window(self, window: WindowInfo, settings: TranslatorSettings) -> str:
        if settings.translator not in {"deepseek", "grok"}:
            return ""
        key = clean_work_title(window.title)
        if not key:
            return ""
        if key == self.current_work_context_key:
            return self.current_work_context
        if key not in self.work_context_cache:
            self.root.after(0, self._set_status, self._tr("status_lookup_wiki"), self._tr("title_lookup_wiki"))
            self.work_context_cache[key] = fetch_wiki_context(key)
        self.current_work_context_key = key
        self.current_work_context = self.work_context_cache.get(key, "")
        return self.current_work_context

    def _remember_source_line(self, text: str) -> None:
        if not text or (self.recent_source_lines and self.recent_source_lines[-1] == text):
            return
        self.recent_source_lines.append(text)
        max_lines = max(self.context_lines_var.get(), 0) + 4
        if len(self.recent_source_lines) > max_lines:
            self.recent_source_lines = self.recent_source_lines[-max_lines:]

    def _cache_key(
        self,
        text: str,
        settings: TranslatorSettings,
        context: list[str],
        work_context: str = "",
        output_language: str = "",
    ) -> str:
        context_key = "\n".join(context) if settings.translator in {"deepseek", "grok"} else ""
        work_key = work_context[:500] if settings.translator in {"deepseek", "grok"} else ""
        language_key = output_language or settings.target_language
        return f"{settings.translator}|{settings.model}|{language_key}|{work_key}|{context_key}|{text}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    config = load_local_settings()
    parser = argparse.ArgumentParser(description="Realtime OCR translator for visual novel game windows.")
    parser.add_argument(
        "--title",
        default=str(config.get("title", "")),
        help="Part of the game window title to capture. Leave empty to select from the window list.",
    )
    parser.add_argument(
        "--target-language",
        default=str(config.get("target_language", DEFAULT_OUTPUT_RIGHT_LANGUAGE)),
        help="Translation target language.",
    )
    parser.add_argument(
        "--left-language",
        default=str(config.get("left_language", DEFAULT_OUTPUT_LEFT_LANGUAGE)),
        help="Language shown in the left output panel.",
    )
    parser.add_argument(
        "--right-language",
        default=str(config.get("right_language", config.get("target_language", DEFAULT_OUTPUT_RIGHT_LANGUAGE))),
        help="Language shown in the right output panel.",
    )
    parser.add_argument(
        "--model",
        default=str(config.get("model", os.environ.get("OPENAI_MODEL", "gpt-5-mini"))),
        help="OpenAI model name.",
    )
    parser.add_argument(
        "--openai-model",
        default=str(config.get("openai_model", config.get("model", os.environ.get("OPENAI_MODEL", "gpt-5-mini")))),
        help="Stored OpenAI model name for the provider config list.",
    )
    parser.add_argument(
        "--openai-url",
        default=str(config.get("openai_url", "https://api.openai.com/v1")),
        help="Stored OpenAI API base URL for the provider config list.",
    )
    parser.add_argument(
        "--openai-api-key",
        default=str(config.get("openai_api_key", config.get("api_key", ""))),
        help="Stored OpenAI API key for the provider config list.",
    )
    parser.add_argument(
        "--ocr-engine",
        default=str(config.get("ocr_engine", "tesseract")),
        choices=("auto", "openai-vision", "tesseract"),
        help="OCR engine. auto uses Tesseract when available, otherwise OpenAI vision.",
    )
    parser.add_argument(
        "--translator",
        default=str(config.get("translator", os.environ.get("TRANSLATOR", "argos"))),
        choices=("argos", "deepseek", "grok", "libretranslate", "openai"),
        help="Text translation backend.",
    )
    parser.add_argument(
        "--libre-url",
        default=str(config.get("libre_url", os.environ.get("LIBRETRANSLATE_URL", "http://127.0.0.1:5000"))),
        help="LibreTranslate base URL.",
    )
    parser.add_argument(
        "--libre-target",
        default=str(config.get("libre_target", "zh-Hans")),
        help="LibreTranslate target language code.",
    )
    parser.add_argument(
        "--deepseek-model",
        default=str(config.get("deepseek_model", os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"))),
        help="DeepSeek model name.",
    )
    parser.add_argument(
        "--deepseek-url",
        default=str(config.get("deepseek_url", os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))),
        help="DeepSeek API base URL.",
    )
    parser.add_argument(
        "--deepseek-api-key",
        "--deepseek-api-key-file",
        dest="deepseek_api_key",
        default=str(config.get("deepseek_api_key", "")),
        help="DeepSeek API key. A legacy text-file path is still accepted for compatibility.",
    )
    parser.add_argument(
        "--grok-model",
        default=str(config.get("grok_model", os.environ.get("GROK_MODEL", "grok-4"))),
        help="Grok model name.",
    )
    parser.add_argument(
        "--grok-url",
        default=str(config.get("grok_url", os.environ.get("GROK_BASE_URL", "https://api.x.ai/v1"))),
        help="Grok/xAI API base URL.",
    )
    parser.add_argument(
        "--grok-api-key",
        "--grok-api-key-file",
        dest="grok_api_key",
        default=str(config.get("grok_api_key", "")),
        help="xAI API key. A legacy text-file path is still accepted for compatibility.",
    )
    parser.add_argument(
        "--api-url",
        default=str(config.get("api_url", os.environ.get("TRANSLATION_API_BASE_URL", ""))),
        help="Unified chat-completions API base URL. Recognizes DeepSeek and xAI/Grok.",
    )
    parser.add_argument(
        "--api-key",
        "--api-key-file",
        dest="api_key",
        default=str(config.get("api_key", "")),
        help="Unified API key for the selected online provider. A legacy text-file path is still accepted.",
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=int(config.get("context_lines", 6)),
        help="Recent OCR lines to send as translation context.",
    )
    parser.add_argument(
        "--stable-reads",
        type=int,
        default=int(config.get("stable_reads", 3)),
        help="OCR must match this many times before refresh.",
    )
    parser.add_argument(
        "--lock-current-line",
        action="store_true",
        default=bool(config.get("lock_current_line", False)),
        help="Keep the current dialogue on screen until unlocked.",
    )
    parser.add_argument(
        "--interval-ms",
        type=int,
        default=int(config.get("interval_ms", 1500)),
        help="OCR polling interval in milliseconds.",
    )
    parser.add_argument(
        "--ui-language",
        default=str(config.get("ui_language", DEFAULT_UI_LANGUAGE)),
        choices=UI_LANGUAGE_OPTIONS,
        help="UI language: auto, zh-CN, or en.",
    )
    parser.add_argument(
        "--output-layout",
        default=str(config.get("output_layout", DEFAULT_OUTPUT_LAYOUT)),
        choices=OUTPUT_LAYOUT_OPTIONS,
        help="Layout of the two output panels: horizontal or vertical.",
    )
    parser.add_argument(
        "--font-family",
        default=str(config.get("font_family", os.environ.get("TRANSLATION_FONT_FAMILY", DEFAULT_OUTPUT_FONT_FAMILY))),
        help="Font family used for translated text display.",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=int(config.get("font_size", os.environ.get("TRANSLATION_FONT_SIZE", str(DEFAULT_OUTPUT_FONT_SIZE)))),
        help="Font size used for translated text display.",
    )
    parser.add_argument("--left", type=float, default=float(config.get("left", 0.05)), help="Subtitle crop left ratio.")
    parser.add_argument("--top", type=float, default=float(config.get("top", 0.62)), help="Subtitle crop top ratio.")
    parser.add_argument("--right", type=float, default=float(config.get("right", 0.95)), help="Subtitle crop right ratio.")
    parser.add_argument("--bottom", type=float, default=float(config.get("bottom", 0.95)), help="Subtitle crop bottom ratio.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    configure_tesseract()
    args = parse_args(argv)
    root = tk.Tk()
    app = TranslatorApp(root, args)

    def close_app() -> None:
        app.save_settings()
        app.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_app)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

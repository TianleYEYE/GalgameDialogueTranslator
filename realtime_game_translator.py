import argparse
import base64
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import tkinter as tk
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


DEFAULT_OPENAI_KEY_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "OpenAI Key.txt")
DEFAULT_DEEPSEEK_KEY_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "Deepseek Key.txt")
DEFAULT_GROK_KEY_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "Grok Key.txt")
DEFAULT_TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
OCR_SIMILARITY_THRESHOLD = 0.78
WIKI_USER_AGENT = "GalgameDialogueTranslator/0.1 (https://github.com/TianleYEYE/GalgameDialogueTranslator)"

API_PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_file": DEFAULT_OPENAI_KEY_FILE,
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
        "key_file": DEFAULT_DEEPSEEK_KEY_FILE,
        "models": ("deepseek-v4-flash", "deepseek-v4-pro"),
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "key_file": DEFAULT_GROK_KEY_FILE,
        "models": ("grok-4", "grok-4.20-reasoning", "grok-4-fast", "grok-3", "grok-3-mini"),
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


def find_window(title_part: str) -> WindowInfo | None:
    needle = title_part.casefold().strip()
    for window in list_capture_windows():
        if not needle or needle in window.title.casefold():
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
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        if right - left >= 240 and bottom - top >= 160:
            windows.append(WindowInfo(hwnd, title, (left, top, right, bottom)))
        return True

    win32gui.EnumWindows(visit, None)
    return windows


def clamp_ratio(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def select_region_for_window(
    root: tk.Tk,
    window: WindowInfo,
    on_selected: Callable[[tuple[float, float, float, float]], None],
    on_cancelled: Callable[[], None],
) -> None:
    left, top, right, bottom = window.rect
    width = max(right - left, 1)
    height = max(bottom - top, 1)

    selector = tk.Toplevel(root)
    selector.overrideredirect(True)
    selector.attributes("-topmost", True)
    selector.attributes("-alpha", 0.35)
    selector.configure(bg="black")
    selector.geometry(f"{width}x{height}+{left}+{top}")
    selector.focus_force()
    selector.grab_set()

    canvas = tk.Canvas(selector, cursor="crosshair", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
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
        if line:
            lines.append(line)
    text = " ".join(lines)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    return text.strip()


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    scale = 2
    image = image.resize((image.width * scale, image.height * scale))
    return image.point(lambda px: 255 if px > 150 else 0)


def translate_with_openai(text: str, target_language: str, model: str, base_url: str, api_key_file: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or read_secret_from_file(api_key_file)
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
    api_key_file: str,
    api_key_env: str,
    work_context: str = "",
) -> str:
    api_key = os.environ.get(api_key_env, "").strip() or read_secret_from_file(api_key_file)
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
    api_key_file: str,
    work_context: str = "",
) -> str:
    return translate_with_chat_completions(
        "DeepSeek",
        text,
        context_lines,
        target_language,
        model,
        base_url,
        api_key_file,
        "DEEPSEEK_API_KEY",
        work_context,
    )


def translate_with_grok(
    text: str,
    context_lines: list[str],
    target_language: str,
    model: str,
    base_url: str,
    api_key_file: str,
    work_context: str = "",
) -> str:
    return translate_with_chat_completions(
        "Grok",
        text,
        context_lines,
        target_language,
        model,
        base_url,
        api_key_file,
        "XAI_API_KEY",
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
            args.api_key_file or args.deepseek_api_key_file,
            work_context,
        )
    if args.translator == "grok":
        return translate_with_grok(
            text,
            context_lines,
            args.target_language,
            args.model,
            args.api_url or args.grok_url,
            args.api_key_file or args.grok_api_key_file,
            work_context,
        )
    return translate_with_openai(
        text,
        args.target_language,
        args.model,
        args.api_url or API_PROVIDER_CONFIGS["openai"]["base_url"],
        args.api_key_file or API_PROVIDER_CONFIGS["openai"]["key_file"],
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
    deepseek_api_key_file: str
    grok_model: str
    grok_url: str
    grok_api_key_file: str
    api_url: str
    api_key_file: str
    context_lines: int
    stable_reads: int


def translate_image_with_openai(
    image: Image.Image,
    target_language: str,
    model: str,
    base_url: str,
    api_key_file: str,
) -> tuple[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or read_secret_from_file(api_key_file)
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


class TranslatorApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.root.title("Game Dialogue Translator")
        self.root.geometry("580x560")
        self.root.attributes("-topmost", True)

        self.running = False
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.last_ocr_text = ""
        self.translation_cache: dict[str, str] = {}
        self.status_text = tk.StringVar(value="Ready")

        self.title_var = tk.StringVar(value=args.title)
        self.target_language_var = tk.StringVar(value=args.target_language)
        self.model_var = tk.StringVar(value=args.model)
        self.ocr_engine_var = tk.StringVar(value=args.ocr_engine)
        self.translator_var = tk.StringVar(value=args.translator)
        self.libre_url_var = tk.StringVar(value=args.libre_url)
        self.libre_target_var = tk.StringVar(value=args.libre_target)
        self.deepseek_model_var = tk.StringVar(value=args.deepseek_model)
        self.deepseek_url_var = tk.StringVar(value=args.deepseek_url)
        self.deepseek_api_key_file_var = tk.StringVar(value=args.deepseek_api_key_file)
        self.grok_model_var = tk.StringVar(value=args.grok_model)
        self.grok_url_var = tk.StringVar(value=args.grok_url)
        self.grok_api_key_file_var = tk.StringVar(value=args.grok_api_key_file)
        initial_api_url = args.api_url or self._default_api_url(args.translator)
        initial_api_key_file = args.api_key_file or self._default_api_key_file(args.translator)
        self.api_url_var = tk.StringVar(value=initial_api_url)
        self.api_key_file_var = tk.StringVar(value=initial_api_key_file)
        self.context_lines_var = tk.IntVar(value=args.context_lines)
        self.stable_reads_var = tk.IntVar(value=args.stable_reads)
        self.interval_var = tk.IntVar(value=args.interval_ms)
        self.left_var = tk.DoubleVar(value=args.left)
        self.top_var = tk.DoubleVar(value=args.top)
        self.right_var = tk.DoubleVar(value=args.right)
        self.bottom_var = tk.DoubleVar(value=args.bottom)
        self.pending_ocr_text = ""
        self.pending_ocr_count = 0
        self.last_translated_ocr_text = ""
        self.last_displayed_translation = ""
        self.recent_source_lines: list[str] = []
        self.window_choice_var = tk.StringVar(value="")
        self.window_choices: dict[str, WindowInfo] = {}
        self.work_context_cache: dict[str, str] = {}
        self.current_work_context = ""
        self.current_work_context_key = ""
        self.window_combo: ttk.Combobox | None = None
        self.model_combo: ttk.Combobox | None = None

        self._build_ui()
        self.refresh_window_list()
        self._sync_api_provider_fields()
        self.translator_var.trace_add("write", lambda *_args: self._on_provider_changed())
        self.api_url_var.trace_add("write", lambda *_args: self._on_api_url_changed())

    def _build_ui(self) -> None:
        root = self.root
        controls = ttk.Frame(root, padding=8)
        controls.pack(fill="x")

        ttk.Label(controls, text="Window title").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.title_var, width=26).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(controls, text="Refresh windows", command=self.refresh_window_list).grid(row=0, column=2, padx=3)
        ttk.Button(controls, text="Place beside", command=self.place_beside_game).grid(row=0, column=3, padx=3)

        ttk.Label(controls, text="Target language").grid(row=1, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.target_language_var, width=14).grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(controls, text="Model").grid(row=1, column=2, sticky="e")
        self.model_combo = ttk.Combobox(controls, textvariable=self.model_var, width=18)
        self.model_combo.grid(row=1, column=3, sticky="ew", padx=3)

        ttk.Label(controls, text="Interval ms").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(controls, from_=500, to=10000, increment=250, textvariable=self.interval_var, width=10).grid(
            row=2, column=1, sticky="w", padx=6
        )
        ttk.Button(controls, text="Start", command=self.start).grid(row=2, column=2, padx=3)
        ttk.Button(controls, text="Stop", command=self.stop).grid(row=2, column=3, padx=3, sticky="w")

        ttk.Label(controls, text="OCR").grid(row=3, column=0, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.ocr_engine_var,
            values=("auto", "openai-vision", "tesseract"),
            width=16,
            state="readonly",
        ).grid(row=3, column=1, sticky="w", padx=6)
        ttk.Label(controls, text="Translator").grid(row=3, column=2, sticky="e")
        ttk.Combobox(
            controls,
            textvariable=self.translator_var,
            values=("argos", "deepseek", "grok", "libretranslate", "openai"),
            width=16,
            state="readonly",
        ).grid(row=3, column=3, sticky="w", padx=3)

        ttk.Label(controls, text="Libre URL").grid(row=4, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.libre_url_var, width=26).grid(row=4, column=1, sticky="ew", padx=6)
        ttk.Label(controls, text="Libre target").grid(row=4, column=2, sticky="e")
        ttk.Entry(controls, textvariable=self.libre_target_var, width=8).grid(row=4, column=3, sticky="w", padx=3)

        ttk.Label(controls, text="API URL").grid(row=5, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.api_url_var, width=32).grid(row=5, column=1, sticky="ew", padx=6)
        ttk.Label(controls, text="Key file").grid(row=5, column=2, sticky="e")
        ttk.Entry(controls, textvariable=self.api_key_file_var, width=24).grid(row=5, column=3, sticky="ew", padx=3)

        ttk.Label(controls, text="Window list").grid(row=6, column=0, sticky="w")
        self.window_combo = ttk.Combobox(
            controls,
            textvariable=self.window_choice_var,
            values=(),
            width=42,
            state="readonly",
        )
        self.window_combo.grid(row=6, column=1, columnspan=3, sticky="ew", padx=6, pady=(3, 0))
        self.window_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_window_selected())

        ttk.Label(controls, text="Context").grid(row=7, column=0, sticky="w")
        ttk.Spinbox(controls, from_=0, to=12, increment=1, textvariable=self.context_lines_var, width=8).grid(
            row=7, column=1, sticky="w", padx=6
        )
        ttk.Label(controls, text="Stable reads").grid(row=7, column=2, sticky="e")
        ttk.Spinbox(controls, from_=1, to=5, increment=1, textvariable=self.stable_reads_var, width=8).grid(
            row=7, column=3, sticky="w", padx=3
        )

        crop = ttk.LabelFrame(root, text="Subtitle crop area", padding=8)
        crop.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(crop, text="Select area", command=self.select_capture_area).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=(0, 10), pady=(0, 6)
        )
        for index, (label, var) in enumerate(
            [
                ("Left", self.left_var),
                ("Top", self.top_var),
                ("Right", self.right_var),
                ("Bottom", self.bottom_var),
            ]
        ):
            ttk.Label(crop, text=label).grid(row=1, column=index * 2, sticky="e")
            ttk.Spinbox(crop, from_=0.0, to=1.0, increment=0.01, textvariable=var, width=7).grid(
                row=1, column=index * 2 + 1, padx=(3, 10)
            )

        self.output = tk.Text(root, wrap="word", font=("Microsoft YaHei UI", 13), height=11)
        self.output.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.output.insert(
            "1.0",
            "Select a game window, then click Start.\n"
            "The default crop captures the lower part of the game window.",
        )

        status = ttk.Label(root, textvariable=self.status_text, anchor="w", padding=(8, 0, 8, 8))
        status.pack(fill="x")
        controls.columnconfigure(1, weight=1)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        self.status_text.set("Running")

    def stop(self) -> None:
        self.running = False
        self.stop_event.set()
        self.status_text.set("Stopped")

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
                "Window not found",
                "Select a window from the list or enter part of the game window title.",
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
                "Window not found",
                "Select a window from the list or enter part of the game window title before selecting an area.",
            )
            return
        self.status_text.set("Drag over the game window to select the subtitle area")

        def apply_region(region: tuple[float, float, float, float]) -> None:
            left, top, right, bottom = region
            self.left_var.set(round(left, 3))
            self.top_var.set(round(top, 3))
            self.right_var.set(round(right, 3))
            self.bottom_var.set(round(bottom, 3))
            self.status_text.set("Capture area updated")

        def cancel_region() -> None:
            self.status_text.set("Capture area selection cancelled")

        select_region_for_window(self.root, window, apply_region, cancel_region)

    def _default_api_url(self, provider: str) -> str:
        return str(API_PROVIDER_CONFIGS.get(provider, {}).get("base_url", ""))

    def _default_api_key_file(self, provider: str) -> str:
        return str(API_PROVIDER_CONFIGS.get(provider, {}).get("key_file", ""))

    def _on_provider_changed(self) -> None:
        provider = self.translator_var.get().strip()
        if provider in API_PROVIDER_CONFIGS:
            self.api_url_var.set(self._default_api_url(provider))
            self.api_key_file_var.set(self._default_api_key_file(provider))
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
        if provider in API_PROVIDER_CONFIGS and not self.api_key_file_var.get().strip():
            self.api_key_file_var.set(self._default_api_key_file(provider))

    def _set_output(self, text: str) -> None:
        if text == self.last_displayed_translation:
            return
        self.last_displayed_translation = text
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    def _loop(self) -> None:
        with mss.mss() as capture:
            while not self.stop_event.is_set():
                try:
                    window = self.window_choices.get(self.window_choice_var.get()) or find_window(self.title_var.get())
                    if not window:
                        self.root.after(0, self.status_text.set, "找不到游戏窗口")
                        time.sleep(1)
                        continue

                    image = self._capture_subtitle_area(capture, window)
                    ocr_text, direct_translation = self._read_or_translate_image(image)
                    if direct_translation and direct_translation != self.translation_cache.get("__last_direct__"):
                        self.translation_cache["__last_direct__"] = direct_translation
                        self.root.after(0, self._set_output, direct_translation)
                        self.root.after(0, self.status_text.set, "已更新")
                        time.sleep(max(self.interval_var.get(), 500) / 1000)
                        continue
                    if (
                        ocr_text
                        and self.last_translated_ocr_text
                        and ocr_texts_are_similar(ocr_text, self.last_translated_ocr_text)
                    ):
                        self.last_ocr_text = ocr_text
                        self.root.after(0, self.status_text.set, "同一句台词，保持当前译文")
                    elif ocr_text and ocr_text != self.last_ocr_text:
                        if not self._ocr_is_stable(ocr_text):
                            self.root.after(0, self.status_text.set, "等待文字稳定")
                            time.sleep(max(self.interval_var.get(), 500) / 1000)
                            continue

                        ocr_text = self.pending_ocr_text
                        self.root.after(0, self.status_text.set, "正在翻译")
                        settings = self._settings()
                        context = self._translation_context()
                        work_context = self._work_context_for_window(window, settings)
                        cache_key = self._cache_key(ocr_text, settings, context, work_context)
                        translation = self.translation_cache.get(cache_key)
                        if translation is None:
                            translation = translate_text(ocr_text, settings, context, work_context)
                            self.translation_cache[cache_key] = translation
                        self.last_ocr_text = ocr_text
                        self.last_translated_ocr_text = ocr_text
                        self._remember_source_line(ocr_text)
                        self.root.after(0, self._set_output, translation)
                        self.root.after(0, self.status_text.set, "已更新")
                    else:
                        self.root.after(0, self.status_text.set, "未发现新文本")
                except Exception as exc:
                    self.root.after(0, self.status_text.set, f"错误：{exc}")

                time.sleep(max(self.interval_var.get(), 500) / 1000)

    def _capture_subtitle_area(self, capture: mss.mss, window: WindowInfo) -> Image.Image:
        left, top, right, bottom = window.rect
        width = right - left
        height = bottom - top

        crop_left = left + int(width * self.left_var.get())
        crop_top = top + int(height * self.top_var.get())
        crop_right = left + int(width * self.right_var.get())
        crop_bottom = top + int(height * self.bottom_var.get())

        monitor = {
            "left": crop_left,
            "top": crop_top,
            "width": max(crop_right - crop_left, 20),
            "height": max(crop_bottom - crop_top, 20),
        }
        grabbed = capture.grab(monitor)
        return Image.frombytes("RGB", grabbed.size, grabbed.rgb)

    def _ocr(self, image: Image.Image) -> str:
        prepared = preprocess_for_ocr(image)
        config = "--psm 6"
        text = pytesseract.image_to_string(prepared, lang="eng", config=config)
        return normalize_ocr_text(text)

    def _read_or_translate_image(self, image: Image.Image) -> tuple[str, str]:
        engine = self.ocr_engine_var.get()
        has_tesseract = tesseract_is_available()
        if engine == "tesseract" or (engine == "auto" and has_tesseract):
            return self._ocr(image), ""
        if engine == "auto" or engine == "openai-vision":
            self.root.after(0, self.status_text.set, "正在识别并翻译截图")
            return translate_image_with_openai(
                image,
                self.target_language_var.get().strip() or "Simplified Chinese",
                self.model_var.get().strip() or "gpt-4o-mini",
                self.api_url_var.get().strip() or API_PROVIDER_CONFIGS["openai"]["base_url"],
                self.api_key_file_var.get().strip() or API_PROVIDER_CONFIGS["openai"]["key_file"],
            )
        return "", "未知识别方式。"

    def _settings(self) -> TranslatorSettings:
        return TranslatorSettings(
            translator=self.translator_var.get().strip() or "argos",
            target_language=self.target_language_var.get().strip() or "Simplified Chinese",
            model=self.model_var.get().strip() or "gpt-5-mini",
            libre_url=self.libre_url_var.get().strip() or "http://127.0.0.1:5000",
            libre_target=self.libre_target_var.get().strip() or "zh-Hans",
            deepseek_model=self.deepseek_model_var.get().strip() or "deepseek-v4-flash",
            deepseek_url=self.deepseek_url_var.get().strip() or "https://api.deepseek.com",
            deepseek_api_key_file=self.deepseek_api_key_file_var.get().strip() or DEFAULT_DEEPSEEK_KEY_FILE,
            grok_model=self.grok_model_var.get().strip() or "grok-4",
            grok_url=self.grok_url_var.get().strip() or "https://api.x.ai/v1",
            grok_api_key_file=self.grok_api_key_file_var.get().strip() or DEFAULT_GROK_KEY_FILE,
            api_url=self.api_url_var.get().strip(),
            api_key_file=self.api_key_file_var.get().strip(),
            context_lines=max(self.context_lines_var.get(), 0),
            stable_reads=max(self.stable_reads_var.get(), 1),
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
            self.root.after(0, self.status_text.set, "Looking up wiki context")
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

    def _cache_key(self, text: str, settings: TranslatorSettings, context: list[str], work_context: str = "") -> str:
        context_key = "\n".join(context) if settings.translator in {"deepseek", "grok"} else ""
        work_key = work_context[:500] if settings.translator in {"deepseek", "grok"} else ""
        return f"{settings.translator}|{settings.model}|{settings.target_language}|{work_key}|{context_key}|{text}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Realtime OCR translator for visual novel game windows.")
    parser.add_argument("--title", default="", help="Part of the game window title to capture. Leave empty to select from the window list.")
    parser.add_argument("--target-language", default="Simplified Chinese", help="Translation target language.")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5-mini"), help="OpenAI model name.")
    parser.add_argument(
        "--ocr-engine",
        default="tesseract",
        choices=("auto", "openai-vision", "tesseract"),
        help="OCR engine. auto uses Tesseract when available, otherwise OpenAI vision.",
    )
    parser.add_argument(
        "--translator",
        default=os.environ.get("TRANSLATOR", "argos"),
        choices=("argos", "deepseek", "grok", "libretranslate", "openai"),
        help="Text translation backend.",
    )
    parser.add_argument(
        "--libre-url",
        default=os.environ.get("LIBRETRANSLATE_URL", "http://127.0.0.1:5000"),
        help="LibreTranslate base URL.",
    )
    parser.add_argument("--libre-target", default="zh-Hans", help="LibreTranslate target language code.")
    parser.add_argument(
        "--deepseek-model",
        default=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        help="DeepSeek model name.",
    )
    parser.add_argument(
        "--deepseek-url",
        default=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        help="DeepSeek API base URL.",
    )
    parser.add_argument(
        "--deepseek-api-key-file",
        default=os.environ.get("DEEPSEEK_API_KEY_FILE", DEFAULT_DEEPSEEK_KEY_FILE),
        help="Path to a text file containing the DeepSeek API key.",
    )
    parser.add_argument(
        "--grok-model",
        default=os.environ.get("GROK_MODEL", "grok-4"),
        help="Grok model name.",
    )
    parser.add_argument(
        "--grok-url",
        default=os.environ.get("GROK_BASE_URL", "https://api.x.ai/v1"),
        help="Grok/xAI API base URL.",
    )
    parser.add_argument(
        "--grok-api-key-file",
        default=os.environ.get("GROK_API_KEY_FILE", DEFAULT_GROK_KEY_FILE),
        help="Path to a text file containing the xAI API key.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("TRANSLATION_API_BASE_URL", ""),
        help="Unified chat-completions API base URL. Recognizes DeepSeek and xAI/Grok.",
    )
    parser.add_argument(
        "--api-key-file",
        default=os.environ.get("TRANSLATION_API_KEY_FILE", ""),
        help="Unified API key file for DeepSeek or xAI/Grok.",
    )
    parser.add_argument("--context-lines", type=int, default=6, help="Recent OCR lines to send as translation context.")
    parser.add_argument("--stable-reads", type=int, default=3, help="OCR must match this many times before refresh.")
    parser.add_argument("--interval-ms", type=int, default=1500, help="OCR polling interval in milliseconds.")
    parser.add_argument("--left", type=float, default=0.05, help="Subtitle crop left ratio.")
    parser.add_argument("--top", type=float, default=0.62, help="Subtitle crop top ratio.")
    parser.add_argument("--right", type=float, default=0.95, help="Subtitle crop right ratio.")
    parser.add_argument("--bottom", type=float, default=0.95, help="Subtitle crop bottom ratio.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    configure_tesseract()
    args = parse_args(argv)
    root = tk.Tk()
    app = TranslatorApp(root, args)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

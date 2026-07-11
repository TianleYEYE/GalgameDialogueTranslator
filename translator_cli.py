from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import tkinter as tk
from datetime import datetime, timezone

import mss
import pytesseract

from realtime_game_translator import (
    DEFAULT_OUTPUT_FONT_FAMILY,
    DEFAULT_OUTPUT_FONT_SIZE,
    DEFAULT_OUTPUT_LAYOUT,
    append_vocabulary_entry,
    capture_window_image,
    configure_tesseract,
    find_window,
    find_window_by_reference,
    list_capture_windows,
    load_vocabulary_entries,
    preprocess_for_ocr,
    normalize_ocr_text,
    read_text_with_openai,
    select_region_for_window,
    TranslatorSettings,
    translate_text,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge commands for the Tauri UI.")
    subparsers = parser.add_subparsers(dest="command")

    translate_parser = subparsers.add_parser("translate")
    add_translate_args(translate_parser)

    ocr_parser = subparsers.add_parser("ocr-translate")
    add_translate_args(ocr_parser)
    ocr_parser.add_argument("--window-title", default="")
    ocr_parser.add_argument("--hwnd", type=int, default=0)
    ocr_parser.add_argument("--ocr-engine", default="tesseract")
    ocr_parser.add_argument("--left", type=float, default=0.05)
    ocr_parser.add_argument("--top", type=float, default=0.62)
    ocr_parser.add_argument("--right", type=float, default=0.95)
    ocr_parser.add_argument("--bottom", type=float, default=0.95)

    ocr_only_parser = subparsers.add_parser("ocr")
    ocr_only_parser.add_argument("--window-title", default="")
    ocr_only_parser.add_argument("--hwnd", type=int, default=0)
    ocr_only_parser.add_argument("--ocr-engine", default="tesseract")
    ocr_only_parser.add_argument("--model", default="gpt-4o-mini")
    ocr_only_parser.add_argument("--api-url", default="https://api.openai.com/v1")
    ocr_only_parser.add_argument("--api-key", default="")
    ocr_only_parser.add_argument("--left", type=float, default=0.05)
    ocr_only_parser.add_argument("--top", type=float, default=0.62)
    ocr_only_parser.add_argument("--right", type=float, default=0.95)
    ocr_only_parser.add_argument("--bottom", type=float, default=0.95)

    subparsers.add_parser("list-windows")

    select_area_parser = subparsers.add_parser("select-area")
    select_area_parser.add_argument("--window-title", default="")
    select_area_parser.add_argument("--hwnd", type=int, default=0)

    preview_parser = subparsers.add_parser("preview-area")
    preview_parser.add_argument("--window-title", default="")
    preview_parser.add_argument("--hwnd", type=int, default=0)
    preview_parser.add_argument("--left", type=float, default=0.05)
    preview_parser.add_argument("--top", type=float, default=0.62)
    preview_parser.add_argument("--right", type=float, default=0.95)
    preview_parser.add_argument("--bottom", type=float, default=0.95)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--source", required=True)
    collect_parser.add_argument("--translation", default="")
    collect_parser.add_argument("--source-language", default="")
    collect_parser.add_argument("--target-language", default="")
    collect_parser.add_argument("--window-title", default="")
    collect_parser.add_argument("--kind", default="line")
    collect_parser.add_argument("--note", default="")
    collect_parser.add_argument("--tags", default="")

    subparsers.add_parser("vocabulary")

    update_vocab_parser = subparsers.add_parser("update-vocabulary")
    update_vocab_parser.add_argument("--created-at", required=True)
    update_vocab_parser.add_argument("--source", required=True)
    update_vocab_parser.add_argument("--translation", default=None)
    update_vocab_parser.add_argument("--status", default=None)

    delete_vocab_parser = subparsers.add_parser("delete-vocabulary")
    delete_vocab_parser.add_argument("--created-at", required=True)
    delete_vocab_parser.add_argument("--source", required=True)

    if argv and argv[0] not in {"translate", "ocr-translate", "ocr", "list-windows", "select-area", "preview-area", "collect", "vocabulary", "update-vocabulary", "delete-vocabulary"}:
        argv = ["translate", *argv]
    return parser.parse_args(argv)


def add_translate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text", default="")
    parser.add_argument("--translator", default="deepseek")
    parser.add_argument("--target-language", default="Simplified Chinese")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--api-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--libre-url", default="http://127.0.0.1:5000")
    parser.add_argument("--libre-target", default="zh-Hans")


def settings_from_args(args: argparse.Namespace) -> TranslatorSettings:
    return TranslatorSettings(
        translator=args.translator,
        target_language=args.target_language,
        model=args.model,
        libre_url=args.libre_url,
        libre_target=args.libre_target,
        deepseek_model=args.model,
        deepseek_url=args.api_url,
        deepseek_api_key=args.api_key,
        grok_model=args.model,
        grok_url=args.api_url,
        grok_api_key=args.api_key,
        api_url=args.api_url,
        api_key=args.api_key,
        context_lines=0,
        stable_reads=1,
        output_layout=DEFAULT_OUTPUT_LAYOUT,
        font_family=DEFAULT_OUTPUT_FONT_FAMILY,
        font_size=DEFAULT_OUTPUT_FONT_SIZE,
        left=0.05,
        top=0.62,
        right=0.95,
        bottom=0.95,
    )

def describe_available_windows() -> str:
    windows = list_capture_windows()
    titles = "; ".join(f"{window.title} [{window.hwnd}]" for window in windows[:12])
    return titles or "no visible capture windows"


def capture_window_region(window_title: str, hwnd: int, left_ratio: float, top_ratio: float, right_ratio: float, bottom_ratio: float):
    window = find_window_by_reference(window_title, hwnd or None)
    if window is None:
        raise RuntimeError(f"Window not found: {window_title or hwnd}. Available windows: {describe_available_windows()}")

    screenshot = capture_window_image(window)
    width = screenshot.width
    height = screenshot.height
    crop_left = max(min(int(width * left_ratio), width - 1), 0)
    crop_top = max(min(int(height * top_ratio), height - 1), 0)
    crop_right = max(min(int(width * right_ratio), width), crop_left + 1)
    crop_bottom = max(min(int(height * bottom_ratio), height), crop_top + 1)
    image = screenshot.crop((crop_left, crop_top, crop_right, crop_bottom))
    return image, {
        "left": crop_left,
        "top": crop_top,
        "width": image.width,
        "height": image.height,
        "window_width": width,
        "window_height": height,
    }


def capture_ocr_text(args: argparse.Namespace) -> str:
    configure_tesseract()
    image, _monitor = capture_window_region(args.window_title, getattr(args, "hwnd", 0), args.left, args.top, args.right, args.bottom)
    if args.ocr_engine == "openai-vision":
        return read_text_with_openai(image, args.model, args.api_url, args.api_key)
    prepared = preprocess_for_ocr(image)
    return normalize_ocr_text(pytesseract.image_to_string(prepared, lang="eng", config="--psm 6"))


def capture_region_image(args: argparse.Namespace) -> dict[str, object]:
    image, monitor = capture_window_region(args.window_title, args.hwnd, args.left, args.top, args.right, args.bottom)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "data_url": f"data:image/png;base64,{encoded}",
        "width": image.width,
        "height": image.height,
        "capture_left": monitor["left"],
        "capture_top": monitor["top"],
        "window_width": monitor["window_width"],
        "window_height": monitor["window_height"],
    }


def print_json(payload: dict[str, object]) -> None:
    body = json.dumps(payload, ensure_ascii=False)
    try:
        print(body)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((body + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()


def select_area(window_title: str, hwnd: int) -> dict[str, object]:
    window = find_window_by_reference(window_title, hwnd or None)
    if window is None:
        raise RuntimeError(f"Window not found: {window_title or hwnd}. Available windows: {describe_available_windows()}")

    root = tk.Tk()
    root.withdraw()
    result: dict[str, object] = {"cancelled": True}

    def apply_region(region: tuple[float, float, float, float]) -> None:
        nonlocal result
        left, top, right, bottom = region
        result = {
            "cancelled": False,
            "left": round(left, 3),
            "top": round(top, 3),
            "right": round(right, 3),
            "bottom": round(bottom, 3),
        }
        root.quit()

    def cancel_region() -> None:
        root.quit()

    select_region_for_window(root, window, apply_region, cancel_region)
    root.mainloop()
    root.destroy()
    return result


def update_vocabulary_entry(created_at: str, source: str, translation: str | None = None, status: str | None = None) -> dict[str, object]:
    from realtime_game_translator import ensure_vocabulary_file

    path = ensure_vocabulary_file()
    entries = load_vocabulary_entries()
    updated = False
    for entry in entries:
        if str(entry.get("created_at", "")) == created_at and str(entry.get("source", "")) == source:
            if translation is not None:
                entry["translation"] = translation
            if status is not None:
                entry["status"] = status
            updated = True
            break
    if not updated:
        return {"ok": False, "updated": False}
    with open(path, "w", encoding="utf-8") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "updated": True}


def delete_vocabulary_entry(created_at: str, source: str) -> dict[str, object]:
    from realtime_game_translator import ensure_vocabulary_file

    path = ensure_vocabulary_file()
    entries = load_vocabulary_entries()
    remaining = [
        entry
        for entry in entries
        if not (str(entry.get("created_at", "")) == created_at and str(entry.get("source", "")) == source)
    ]
    deleted = len(remaining) != len(entries)
    if deleted:
        with open(path, "w", encoding="utf-8") as file:
            for entry in remaining:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"ok": True, "deleted": deleted}


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    command = args.command or "translate"

    if command == "list-windows":
        print_json(
            {
                "windows": [
                    {"title": window.title, "hwnd": window.hwnd, "label": f"{window.title} [{window.hwnd}]"}
                    for window in list_capture_windows()
                ]
            }
        )
        return 0

    if command == "select-area":
        print_json(select_area(args.window_title, args.hwnd))
        return 0

    if command == "preview-area":
        print_json(capture_region_image(args))
        return 0

    if command == "ocr":
        print_json({"source": capture_ocr_text(args)})
        return 0

    if command == "collect":
        append_vocabulary_entry(
            {
                "source": args.source,
                "translation": args.translation,
                "source_language": args.source_language,
                "target_language": args.target_language,
                "window_title": args.window_title,
                "kind": args.kind,
                "note": args.note,
                "tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
                "status": "new",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        print_json({"ok": True})
        return 0

    if command == "vocabulary":
        entries = load_vocabulary_entries()
        print_json({"entries": entries, "count": len(entries)})
        return 0

    if command == "update-vocabulary":
        print_json(update_vocabulary_entry(args.created_at, args.source, args.translation, args.status))
        return 0

    if command == "delete-vocabulary":
        print_json(delete_vocabulary_entry(args.created_at, args.source))
        return 0

    settings = settings_from_args(args)
    source_text = args.text
    if command == "ocr-translate":
        source_text = capture_ocr_text(args)

    translated = translate_text(source_text, settings) if source_text else ""
    print_json({"source": source_text, "translation": translated})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

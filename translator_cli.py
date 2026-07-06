from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import mss
import pytesseract

from realtime_game_translator import (
    DEFAULT_OUTPUT_FONT_FAMILY,
    DEFAULT_OUTPUT_FONT_SIZE,
    DEFAULT_OUTPUT_LAYOUT,
    append_vocabulary_entry,
    configure_tesseract,
    find_window,
    list_capture_windows,
    preprocess_for_ocr,
    normalize_ocr_text,
    read_text_with_openai,
    TranslatorSettings,
    translate_text,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bridge commands for the Tauri UI.")
    subparsers = parser.add_subparsers(dest="command")

    translate_parser = subparsers.add_parser("translate")
    add_translate_args(translate_parser)

    ocr_parser = subparsers.add_parser("ocr-translate")
    add_translate_args(ocr_parser)
    ocr_parser.add_argument("--window-title", default="")
    ocr_parser.add_argument("--ocr-engine", default="tesseract")
    ocr_parser.add_argument("--left", type=float, default=0.05)
    ocr_parser.add_argument("--top", type=float, default=0.62)
    ocr_parser.add_argument("--right", type=float, default=0.95)
    ocr_parser.add_argument("--bottom", type=float, default=0.95)

    subparsers.add_parser("list-windows")

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--source", required=True)
    collect_parser.add_argument("--translation", default="")
    collect_parser.add_argument("--source-language", default="")
    collect_parser.add_argument("--target-language", default="")
    collect_parser.add_argument("--window-title", default="")
    collect_parser.add_argument("--kind", default="line")
    collect_parser.add_argument("--note", default="")
    collect_parser.add_argument("--tags", default="")

    if argv and argv[0] not in {"translate", "ocr-translate", "list-windows", "collect"}:
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


def capture_ocr_text(args: argparse.Namespace) -> str:
    configure_tesseract()
    window = find_window(args.window_title)
    if window is None:
        raise RuntimeError("Window not found")

    left, top, right, bottom = window.rect
    width = right - left
    height = bottom - top
    monitor = {
        "left": left + int(width * args.left),
        "top": top + int(height * args.top),
        "width": max(int(width * (args.right - args.left)), 20),
        "height": max(int(height * (args.bottom - args.top)), 20),
    }
    with mss.mss() as capture:
        grabbed = capture.grab(monitor)
    from PIL import Image

    image = Image.frombytes("RGB", grabbed.size, grabbed.rgb)
    if args.ocr_engine == "openai-vision":
        return read_text_with_openai(image, args.model, args.api_url, args.api_key)
    prepared = preprocess_for_ocr(image)
    return normalize_ocr_text(pytesseract.image_to_string(prepared, lang="eng", config="--psm 6"))


def print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False))


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
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        print_json({"ok": True})
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

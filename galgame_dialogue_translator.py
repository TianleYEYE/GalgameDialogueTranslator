from realtime_game_translator import main


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--title",
                "Little Busters! English Edition",
                "--ocr-engine",
                "tesseract",
                "--translator",
                "grok",
                "--target-language",
                "Simplified Chinese",
                "--model",
                "grok-4",
                "--api-url",
                "https://api.x.ai/v1",
                "--context-lines",
                "6",
                "--stable-reads",
                "3",
            ]
        )
    )

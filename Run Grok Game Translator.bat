@echo off
setlocal
set PATH=%PATH%;C:\Program Files\Tesseract-OCR
start "" "%~dp0dist\GrokGameTranslator\GrokGameTranslator.exe"

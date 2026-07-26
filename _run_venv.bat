@echo off
title ShadPs4Plus Pkg Extractor GUI
if not exist "venv\Scripts\activate.bat" (
    echo [ОШИБКА] Виртуальное окружение 'venv' не найдено.
    echo Создайте его командой: python -m venv venv
    pause
    exit /b
)

call venv\Scripts\activate.bat
start "" pythonw PkgExtractor_GUI.py
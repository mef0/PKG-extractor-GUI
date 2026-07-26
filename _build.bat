@echo off
title Сборка PkgExtractor GUI
chcp 65001 > nul
echo ===================================================
echo  Запуск автоматической сборки PkgExtractor_GUI.exe
echo ===================================================
echo.

:: 1. Проверка наличия venv (если нет — автосоздание)
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] Создание виртуального окружения 'venv'...
    python -m venv venv
) else (
    echo [1/3] Найдено существующее виртуальное окружение.
)

:: 2. Активация окружения и установка зависимостей
call venv\Scripts\activate.bat
echo [2/3] Проверка и установка требуемых библиотек (PyQt6, PyInstaller)...
python -m pip install --upgrade pip > nul
pip install PyQt6 pyinstaller > nul

:: 3. Запуск компиляции PyInstaller
echo [3/3] Компиляция приложения в единый EXE файл...
echo.

pyinstaller --noconfirm --onefile --windowed ^
  --name="PkgExtractor_GUI" ^
  --icon="icon.ico" ^
  --add-data "icon.ico;." ^
  --exclude-module tkinter ^
  --exclude-module matplotlib ^
  --exclude-module scipy ^
  --exclude-module numpy ^
  PkgExtractor_GUI.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo  [УСПЕХ] Сборка успешно завершена!
    echo  Готовый файл: dist\PkgExtractor_GUI.exe
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo  [ОШИБКА] Произошла ошибка при сборке!
    echo ===================================================
)

pause
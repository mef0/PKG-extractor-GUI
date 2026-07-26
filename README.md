
# PKG Extractor GUI

[English](#english) | [Русский](#russian)

---

## Russian

**PKG Extractor GUI** — это удобная графическая оболочка (GUI), написанная на **Python (PyQt6)** для консольной утилиты `pkg_extractor.exe` (v1.1+).

Приложение автоматизирует пакетную обработку `.pkg` архивов: распределяет основной контент, обновления и дополнения (DLC), сопоставляет ID контента и объединяет папки с отслеживанием прогресса в реальном времени.

### 📥 Скачать готовый EXE
Готовый скомпилированный файл для Windows можно скачать в разделе **[Releases / Релизы](../../releases)**.

### ✨ Основные возможности
- 🚀 **Поддержка pkg_extractor v1.1**: Безопасная распаковка файлов любого размера.
- 🧠 **Умное определение Content ID**: Анализирует имена файлов, структуру папок и соседние элементы для точной группировки.
- 🗂️ **Автоматическая сортировка**:
  - **Основной контент и Обновления** → Автоматически объединяются в `Games/CUSAXXXXX/`.
  - **Дополнения (DLC)** → Распаковываются в `_DLC/CUSAXXXXX/`.
- 📁 **Накопительное добавление Drag & Drop**: Пакетное добавление файлов и папок с защитой от дубликатов.

### 🛠️ Сборка EXE файла (Windows CMD)

```cmd
# Создание и активация venv
python -m venv venv
call venv\Scripts\activate.bat

# Установка зависимостей
pip install PyQt6 pyinstaller

# Сборка в один EXE файл
pyinstaller --noconfirm --onefile --windowed --name="PkgExtractor_GUI" --icon="icon.ico" --add-data "icon.ico;." PkgExtractor_GUI.py
```

### 👏 Благодарности
Графическая оболочка разработана для работы с `pkg_extractor.exe` из проекта [shadPS4Plus (AzaharPlus)](https://github.com/AzaharPlus/shadPS4Plus).

---

## English

**PKG Extractor GUI** is a lightweight, modern graphical user interface (GUI) built with **Python & PyQt6** for the `pkg_extractor.exe` (v1.1+) CLI utility.

It simplifies batch processing of `.pkg` archives by automatically categorizing base content, patches/updates, and add-ons (DLCs), matching content IDs, and managing directory merging with real-time progress monitoring.

### 📥 Download Pre-compiled Executable
You can download the latest pre-built Windows standalone executable directly from the **[Releases](../../releases)** section.

### ✨ Features
- 🚀 **pkg_extractor v1.1 Support**: Clean frontend wrapper with full support for large files (>2GB).
- 🧠 **Smart Content ID Detection**: Scans filenames, parent folders, and sibling directory structure to accurately group packages.
- 🗂️ **Automated Category Sorting**:
  - **Base Games & Updates** → Extracted and automatically merged into `Games/CUSAXXXXX/`.
  - **Add-ons / DLCs** → Extracted into `_DLC/CUSAXXXXX/`.
- 📁 **Cumulative Drag & Drop**: Add multiple files or folders seamlessly with duplicate path protection.

### 🛠️ Building Executable (Windows CMD)

```cmd
# Create and activate virtual environment
python -m venv venv
call venv\Scripts\activate.bat

# Install dependencies
pip install PyQt6 pyinstaller

# Build Single Executable
pyinstaller --noconfirm --onefile --windowed --name="PkgExtractor_GUI" --icon="icon.ico" --add-data "icon.ico;." PkgExtractor_GUI.py
```

### 👏 Credits
Designed as a GUI frontend for `pkg_extractor.exe` from the [shadPS4Plus (AzaharPlus)](https://github.com/AzaharPlus/shadPS4Plus) project.

---

import os
import sys
import shutil
import subprocess
import json
import re
import time
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QProgressBar, QGroupBox, QGridLayout, QLineEdit,
                             QFileDialog, QDialog, QDialogButtonBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QLocale
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor, QIcon


def get_resource_path(relative_path):
    """Возвращает корректный путь к файлам как при запуске .py, так и внутри скомпилированного .exe"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
    
# --- Форматирование размера (ГБ / МБ / сотые МБ) ---
def format_size(bytes_val, is_en=False):
    if bytes_val < 0:
        bytes_val = 0
    gb_unit = " GB" if is_en else " ГБ"
    mb_unit = " MB" if is_en else " МБ"
    
    if bytes_val >= 100 * 1024 * 1024:  # >= 100 МБ
        return f"{bytes_val / (1024**3):.2f}{gb_unit}"
    else:  # < 100 МБ
        mb = bytes_val / (1024**2)
        return f"{mb:.2f}{mb_unit}"

# --- Быстрый стековый подсчет размера папки ---
def get_dir_size_fast(path):
    total = 0
    if not os.path.exists(path):
        return 0
    try:
        dirs = [str(path)]
        while dirs:
            current = dirs.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                dirs.append(entry.path)
                        except OSError:
                            continue
            except OSError:
                continue
    except Exception:
        pass
    return total

# --- Автопоиск pkg_extractor.exe СТРОГО в текущем каталоге ---
def auto_detect_pkg_extractor():
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
    else:
        exe_dir = Path(__file__).parent

    candidate1 = exe_dir / "pkg_extractor.exe"
    if candidate1.exists():
        return str(candidate1.resolve())

    candidate2 = Path.cwd() / "pkg_extractor.exe"
    if candidate2.exists():
        return str(candidate2.resolve())

    return "pkg_extractor.exe"

# --- Умный поиск CUSA ID ---
def find_cusa_for_file(pkg_path):
    cusa_pattern = re.compile(r'CUSA\d{5}', re.IGNORECASE)
    
    match = cusa_pattern.search(pkg_path.name)
    if match:
        return match.group(0).upper()
        
    for parent in pkg_path.parents:
        match = cusa_pattern.search(parent.name)
        if match:
            return match.group(0).upper()
            
    return None

# --- Определение типа PKG ---
def classify_pkg_type(pkg_path, is_dlc_flag):
    if is_dlc_flag:
        return "dlc"
        
    name_lower = pkg_path.name.lower()
    
    if any(kw in name_lower for kw in ['update', 'patch', 'backport', 'fix']):
        return "update"
        
    match = re.search(r'-A(\d{2}\.?\d{2})', pkg_path.name, re.IGNORECASE)
    if match:
        ver_str = match.group(1).replace('.', '')
        if ver_str != '0100':
            return "update"
            
    return "game"

# --- Проверка свободного места ---
def check_smart_disk_space(games_dir, dlc_dir, total_size, lang_mgr):
    g_path = Path(games_dir)
    d_path = Path(dlc_dir)
    
    same_drive = False
    try:
        if g_path.exists() and d_path.exists():
            same_drive = (os.stat(g_path).st_dev == os.stat(d_path).st_dev)
        else:
            same_drive = (g_path.anchor.lower() == d_path.anchor.lower())
    except Exception:
        same_drive = (g_path.anchor.lower() == d_path.anchor.lower())

    if same_drive:
        ok, msg = check_disk_space_single(games_dir, total_size, lang_mgr)
        return ok, [f"{lang_mgr.tr('log_drive_shared')}: {msg}"], True
    else:
        ok1, msg1 = check_disk_space_single(games_dir, total_size, lang_mgr)
        ok2, msg2 = check_disk_space_single(dlc_dir, total_size, lang_mgr)
        return (ok1 and ok2), [f"{lang_mgr.tr('log_drive_games')}: {msg1}", f"{lang_mgr.tr('log_drive_dlc')}: {msg2}"], False

def check_disk_space_single(destination_path, total_size_bytes, lang_mgr):
    try:
        Path(destination_path).mkdir(parents=True, exist_ok=True)
        free_space = shutil.disk_usage(destination_path).free
        is_en = (lang_mgr.current_lang != "ru")
        if free_space < total_size_bytes:
            return False, lang_mgr.tr("msg_space_fail").format(format_size(free_space, is_en), format_size(total_size_bytes, is_en))
        return True, lang_mgr.tr("msg_space_ok").format(format_size(free_space, is_en))
    except Exception as e:
        return False, f"Error: {e}"

# --- Менеджер локализации (RU, EN, FA, ES, DE) ---
DEFAULT_LANG_DATA = {
    "ru": {
        "title": "Pkg Extractor GUI",
        "paths_group": "Настройки путей",
        "games_dir": "Games:",
        "dlc_dir": "DLC:",
        "extractor_path": "pkg_extractor.exe:",
        "browse": "Обзор...",
        "theme_dark": "🌙 Тёмная",
        "theme_light": "☀️ Светлая",
        "lang_auto": "Язык/Language Auto",
        "add_files": "Добавить PKG",
        "add_folder": "Добавить папку",
        "clear_list": "Очистить список",
        "start_btn": "🚀 Начать",
        "cancel_btn": "⛔ Отмена",
        "table_file": "Имя файла",
        "table_type": "Тип",
        "table_id": "ID Игры",
        "table_size": "Размер",
        "table_dest": "Назначение",
        "table_status": "Статус",
        "log_title": "Лог операций:",
        "clear_log": "🗑️ Очистить лог",
        "ready": "Готов к работе",
        "drop_hint": "Перетащите сюда .pkg файлы или папки",
        "status_waiting": "Ожидание",
        "status_extracting": "Извлечение...",
        "status_done": "Готово",
        "status_error": "Ошибка",
        "type_game": "Игра",
        "type_patch": "Обновление",
        "type_dlc": "DLC",
        "msg_no_space": "Недостаточно места на диске!",
        "msg_no_extractor": "⚠️ Файл pkg_extractor.exe не найден в текущем каталоге!",
        "msg_enter_id": "Введите CUSA ID для папки:",
        "msg_space_ok": "Достаточно места. Свободно: {}.",
        "msg_space_fail": "Недостаточно места. Свободно: {}, требуется: {}.",
        "status_ready_files": "Готово к обработке {} файлов",
        "log_already_exists": "⚠️ Все добавленные файлы уже находятся в списке.",
        "log_group_skipped": "⚠️ Пропущена группа без ID: {}",
        "log_id_cancelled": "⚠️ Ввод ID отменён.",
        "log_pkg_updated": "📊 Обновленный пакет (Всего файлов: {}, Найдено игр/CUSA: {}):",
        "log_game_stat": "  🆔 {}:\n     🎮 Игр: {} | 🔄 Обновлений: {} | 📦 DLC: {}",
        "log_game_size": "     📦 Объём: {}",
        "log_total_size": "📦 Суммарный размер всех PKG в очереди: {}",
        "log_drive_shared": "💾 Диск (Games & DLC)",
        "log_drive_games": "💾 Папка Games",
        "log_drive_dlc": "💾 Папка DLC",
        "log_cancelled": "❌ Операция отменена пользователем.",
        "log_extracting": "⚙️ Извлечение [{}/{}]: {}",
        "log_try_fake": "🔄 Пробуем с паролем 'fake'...",
        "log_extract_success": "✅ Успешно извлечено: {}",
        "log_merging": "🔄 Объединяем файлы в {}...",
        "log_merge_error": "⚠️ Ошибка при объединении: {}",
        "log_extract_fail": "❌ Ошибка извлечения: {}",
        "log_crit_error": "❌ Критическая ошибка процесса: {}",
        "status_extracted": "Извлечено: {} / {} ({}%)",
        "log_finished_success": "\n🎉 Все операции успешно завершены!",
        "log_elapsed_time": "⏱️ Затраченное время: {}",
        "log_extracted_volume": "📦 Извлечённый объём: {}",
        "log_free_space_single": "💾 Оставшееся свободное место на диске: {}",
        "log_free_space_multi": "💾 Оставшееся свободное место:",
        "time_h_m_s": "{} ч {} мин {} сек",
        "time_m_s": "{} мин {} сек",
        "time_s": "{} сек"
    },
    "en": {
        "title": "Pkg Extractor GUI",
        "paths_group": "Path Settings",
        "games_dir": "Games:",
        "dlc_dir": "DLC:",
        "extractor_path": "pkg_extractor.exe:",
        "browse": "Browse...",
        "theme_dark": "🌙 Dark",
        "theme_light": "☀️ Light",
        "lang_auto": "Language/Язык Auto",
        "add_files": "Add PKG Files",
        "add_folder": "Add Folder",
        "clear_list": "Clear List",
        "start_btn": "🚀 Start",
        "cancel_btn": "⛔ Cancel",
        "table_file": "File Name",
        "table_type": "Type",
        "table_id": "Game ID",
        "table_size": "Size",
        "table_dest": "Destination",
        "table_status": "Status",
        "log_title": "Operation Log:",
        "clear_log": "🗑️ Clear Log",
        "ready": "Ready",
        "drop_hint": "Drag and drop .pkg files or folders here",
        "status_waiting": "Pending",
        "status_extracting": "Extracting...",
        "status_done": "Done",
        "status_error": "Error",
        "type_game": "Game",
        "type_patch": "Update",
        "type_dlc": "DLC",
        "msg_no_space": "Not enough disk space!",
        "msg_no_extractor": "⚠️ Executable pkg_extractor.exe not found in current directory!",
        "msg_enter_id": "Enter CUSA ID for folder:",
        "msg_space_ok": "Sufficient space. Free: {}.",
        "msg_space_fail": "Not enough space. Free: {}, required: {}.",
        "status_ready_files": "Ready to process {} files",
        "log_already_exists": "⚠️ All added files are already in the list.",
        "log_group_skipped": "⚠️ Group without ID skipped: {}",
        "log_id_cancelled": "⚠️ ID entry cancelled.",
        "log_pkg_updated": "📊 Package updated (Total files: {}, Games/CUSA found: {}):",
        "log_game_stat": "  🆔 {}:\n     🎮 Games: {} | 🔄 Updates: {} | 📦 DLC: {}",
        "log_game_size": "     📦 Size: {}",
        "log_total_size": "📦 Total size of all queued PKGs: {}",
        "log_drive_shared": "💾 Drive (Games & DLC)",
        "log_drive_games": "💾 Games Directory",
        "log_drive_dlc": "💾 DLC Directory",
        "log_cancelled": "❌ Operation cancelled by user.",
        "log_extracting": "⚙️ Extracting [{}/{}]: {}",
        "log_try_fake": "🔄 Retrying with 'fake' passcode...",
        "log_extract_success": "✅ Successfully extracted: {}",
        "log_merging": "🔄 Merging files into {}...",
        "log_merge_error": "⚠️ Merge error: {}",
        "log_extract_fail": "❌ Extraction failed: {}",
        "log_crit_error": "❌ Critical process error: {}",
        "status_extracted": "Extracted: {} / {} ({}%)",
        "log_finished_success": "\n🎉 All operations completed successfully!",
        "log_elapsed_time": "⏱️ Elapsed time: {}",
        "log_extracted_volume": "📦 Extracted volume: {}",
        "log_free_space_single": "💾 Remaining free disk space: {}",
        "log_free_space_multi": "💾 Remaining free disk space:",
        "time_h_m_s": "{}h {}m {}s",
        "time_m_s": "{}m {}s",
        "time_s": "{}s"
    },
    "fa": {
        "title": "Pkg Extractor GUI",
        "paths_group": "تنظیمات مسیرها",
        "games_dir": "بازی‌ها:",
        "dlc_dir": "DLC:",
        "extractor_path": "pkg_extractor.exe:",
        "browse": "مرور...",
        "theme_dark": "🌙 تاریک",
        "theme_light": "☀️ روشن",
        "lang_auto": "Language/زبان Auto",
        "add_files": "افزودن PKG",
        "add_folder": "افزودن پوشه",
        "clear_list": "پاکسازی لیست",
        "start_btn": "🚀 شروع",
        "cancel_btn": "⛔ لغو",
        "table_file": "نام فایل",
        "table_type": "نوع",
        "table_id": "شناسه بازی",
        "table_size": "حجم",
        "table_dest": "مقصد",
        "table_status": "وضعیت",
        "log_title": "گزارش عملیات:",
        "clear_log": "🗑️ پاکسازی گزارش",
        "ready": "آماده به کار",
        "drop_hint": "فایل‌ها یا پوشه‌ها را به اینجا بکشید",
        "status_waiting": "در انتظار",
        "status_extracting": "در حال استخراج...",
        "status_done": "انجام شد",
        "status_error": "خطا",
        "type_game": "بازی",
        "type_patch": "به‌روزرسانی",
        "type_dlc": "DLC",
        "msg_no_space": "فضای کافی روی دیسک وجود ندارد!",
        "msg_no_extractor": "⚠️ فایل pkg_extractor.exe یافت نشد!",
        "msg_enter_id": "شناسه CUSA را وارد کنید:",
        "msg_space_ok": "فضای کافی موجود است. فضای آزاد: {}.",
        "msg_space_fail": "فضای کافی وجود ندارد. فضای آزاد: {}، مورد نیاز: {}.",
        "status_ready_files": "آماده برای پردازش {} فایل",
        "log_already_exists": "⚠️ تمام فایل‌های اضافه شده در لیست موجود هستند.",
        "log_group_skipped": "⚠️ گروه بدون شناسه نادیده گرفته شد: {}",
        "log_id_cancelled": "⚠️ ورود شناسه لغو شد.",
        "log_pkg_updated": "📊 بسته به‌روزرسانی شد (تعداد فایل‌ها: {}، شناسه یافت شده: {}):",
        "log_game_stat": "  🆔 {}:\n     🎮 بازی‌ها: {} | 🔄 به‌روزرسانی‌ها: {} | 📦 محتوای افزوده: {}",
        "log_game_size": "     📦 حجم: {}",
        "log_total_size": "📦 حجم کل فایل‌های در صف: {}",
        "log_drive_shared": "💾 دیسک (Games & DLC)",
        "log_drive_games": "💾 پوشه Games",
        "log_drive_dlc": "💾 پوشه DLC",
        "log_cancelled": "❌ عملیات توسط کاربر لغو شد.",
        "log_extracting": "⚙️ در حال استخراج [{}/{}]: {}",
        "log_try_fake": "🔄 تلاش مجدد با رمز عبور 'fake'...",
        "log_extract_success": "✅ با موفقیت استخراج شد: {}",
        "log_merging": "🔄 ادغام فایل‌ها در {}...",
        "log_merge_error": "⚠️ خطا در ادغام: {}",
        "log_extract_fail": "❌ استخراج ناموفق بود: {}",
        "log_crit_error": "❌ خطای بحرانی فرآیند: {}",
        "status_extracted": "استخراج شده: {} / {} ({}%)",
        "log_finished_success": "\n🎉 تمام عملیات با موفقیت انجام شد!",
        "log_elapsed_time": "⏱️ زمان سپری شده: {}",
        "log_extracted_volume": "📦 حجم استخراج شده: {}",
        "log_free_space_single": "💾 فضای آزاد باقی‌مانده دیسک: {}",
        "log_free_space_multi": "💾 فضای آزاد باقی‌مانده:",
        "time_h_m_s": "{}h {}m {}s",
        "time_m_s": "{}m {}s",
        "time_s": "{}s"
    },
    "es": {
        "title": "Pkg Extractor GUI",
        "paths_group": "Configuración de rutas",
        "games_dir": "Juegos:",
        "dlc_dir": "DLC:",
        "extractor_path": "pkg_extractor.exe:",
        "browse": "Examinar...",
        "theme_dark": "🌙 Oscuro",
        "theme_light": "☀️ Claro",
        "lang_auto": "Idioma/Language Auto",
        "add_files": "Añadir PKG",
        "add_folder": "Añadir carpeta",
        "clear_list": "Limpiar lista",
        "start_btn": "🚀 Iniciar",
        "cancel_btn": "⛔ Cancelar",
        "table_file": "Nombre de archivo",
        "table_type": "Tipo",
        "table_id": "ID de juego",
        "table_size": "Tamaño",
        "table_dest": "Destino",
        "table_status": "Estado",
        "log_title": "Registro de operaciones:",
        "clear_log": "🗑️ Limpiar registro",
        "ready": "Listo",
        "drop_hint": "Arrastra archivos .pkg o carpetas aquí",
        "status_waiting": "Pendiente",
        "status_extracting": "Extrayendo...",
        "status_done": "Hecho",
        "status_error": "Error",
        "type_game": "Juego",
        "type_patch": "Actualización",
        "type_dlc": "DLC",
        "msg_no_space": "¡No hay suficiente espacio en disco!",
        "msg_no_extractor": "⚠️ ¡No se encontró pkg_extractor.exe!",
        "msg_enter_id": "Introduce el CUSA ID para la carpeta:",
        "msg_space_ok": "Espacio suficiente. Libre: {}.",
        "msg_space_fail": "Espacio insuficiente. Libre: {}, requerido: {}.",
        "status_ready_files": "Listo para procesar {} archivos",
        "log_already_exists": "⚠️ Todos los archivos añadidos ya están en la lista.",
        "log_group_skipped": "⚠️ Grupo sin ID omitido: {}",
        "log_id_cancelled": "⚠️ Entrada de ID cancelada.",
        "log_pkg_updated": "📊 Paquete actualizado (Archivos totales: {}, Juegos encontrados: {}):",
        "log_game_stat": "  🆔 {}:\n     🎮 Juegos: {} | 🔄 Actualizaciones: {} | 📦 DLC: {}",
        "log_game_size": "     📦 Tamaño: {}",
        "log_total_size": "📦 Tamaño total de los PKG en cola: {}",
        "log_drive_shared": "💾 Disco (Juegos y DLC)",
        "log_drive_games": "💾 Carpeta Juegos",
        "log_drive_dlc": "💾 Carpeta DLC",
        "log_cancelled": "❌ Operación cancelada por el usuario.",
        "log_extracting": "⚙️ Extrayendo [{}/{}]: {}",
        "log_try_fake": "🔄 Reintentando con contraseña 'fake'...",
        "log_extract_success": "✅ Extraído con éxito: {}",
        "log_merging": "🔄 Uniendo archivos en {}...",
        "log_merge_error": "⚠️ Error al unir: {}",
        "log_extract_fail": "❌ Error de extracción: {}",
        "log_crit_error": "❌ Error crítico del proceso: {}",
        "status_extracted": "Extraído: {} / {} ({}%)",
        "log_finished_success": "\n🎉 ¡Todas las operaciones se completaron con éxito!",
        "log_elapsed_time": "⏱️ Tiempo transcurrido: {}",
        "log_extracted_volume": "📦 Volumen extraído: {}",
        "log_free_space_single": "💾 Espacio libre restante en disco: {}",
        "log_free_space_multi": "💾 Espacio libre restante:",
        "time_h_m_s": "{}h {}m {}s",
        "time_m_s": "{}m {}s",
        "time_s": "{}s"
    },
    "de": {
        "title": "Pkg Extractor GUI",
        "paths_group": "Pfadeinstellungen",
        "games_dir": "Spiele:",
        "dlc_dir": "DLC:",
        "extractor_path": "pkg_extractor.exe:",
        "browse": "Durchsuchen...",
        "theme_dark": "🌙 Dunkel",
        "theme_light": "☀️ Hell",
        "lang_auto": "Language/Sprache Auto",
        "add_files": "PKG hinzufügen",
        "add_folder": "Ordner hinzufügen",
        "clear_list": "Liste leeren",
        "start_btn": "🚀 Starten",
        "cancel_btn": "⛔ Abbrechen",
        "table_file": "Dateiname",
        "table_type": "Typ",
        "table_id": "Spiel-ID",
        "table_size": "Größe",
        "table_dest": "Zielpfad",
        "table_status": "Status",
        "log_title": "Aktionsprotokoll:",
        "clear_log": "🗑️ Protokoll leeren",
        "ready": "Bereit",
        "drop_hint": "Ziehen Sie .pkg-Dateien oder Ordner hierher",
        "status_waiting": "Wartend",
        "status_extracting": "Entpacken...",
        "status_done": "Fertig",
        "status_error": "Fehler",
        "type_game": "Spiel",
        "type_patch": "Update",
        "type_dlc": "DLC",
        "msg_no_space": "Nicht genügend Speicherplatz!",
        "msg_no_extractor": "⚠️ pkg_extractor.exe wurde nicht gefunden!",
        "msg_enter_id": "Geben Sie die CUSA-ID für den Ordner ein:",
        "msg_space_ok": "Ausreichend Speicherplatz. Frei: {}.",
        "msg_space_fail": "Nicht genügend Speicherplatz. Frei: {}, Benötigt: {}.",
        "status_ready_files": "Bereit für die Verarbeitung von {} Dateien",
        "log_already_exists": "⚠️ Alle hinzugefügten Dateien befinden sich bereits in der Liste.",
        "log_group_skipped": "⚠️ Gruppe ohne ID übersprungen: {}",
        "log_id_cancelled": "⚠️ ID-Eingabe abgebrochen.",
        "log_pkg_updated": "📊 Paket aktualisiert (Dateien insgesamt: {}, Spiele/CUSA gefunden: {}):",
        "log_game_stat": "  🆔 {}:\n     🎮 Spiele: {} | 🔄 Updates: {} | 📦 DLC: {}",
        "log_game_size": "     📦 Größe: {}",
        "log_total_size": "📦 Gesamtgröße aller PKGs in der Warteschlange: {}",
        "log_drive_shared": "💾 Laufwerk (Spiele & DLC)",
        "log_drive_games": "💾 Spiele-Ordner",
        "log_drive_dlc": "💾 DLC-Ordner",
        "log_cancelled": "❌ Vorgang vom Benutzer abgebrochen.",
        "log_extracting": "⚙️ Entpacken [{}/{}]: {}",
        "log_try_fake": "🔄 Erneuter Versuch mit 'fake'-Passwort...",
        "log_extract_success": "✅ Erfolgreich entpackt: {}",
        "log_merging": "🔄 Zusammenführen der Dateien in {}...",
        "log_merge_error": "⚠️ Fehler beim Zusammenführen: {}",
        "log_extract_fail": "❌ Entpacken fehlgeschlagen: {}",
        "log_crit_error": "❌ Kritischer Prozessfehler: {}",
        "status_extracted": "Entpackt: {} / {} ({}%)",
        "log_finished_success": "\n🎉 Alle Vorgänge erfolgreich abgeschlossen!",
        "log_elapsed_time": "⏱️ Verstrichene Zeit: {}",
        "log_extracted_volume": "📦 Entpacktes Volumen: {}",
        "log_free_space_single": "💾 Verbleibender freier Speicherplatz: {}",
        "log_free_space_multi": "💾 Verbleibender freier Speicherplatz:",
        "time_h_m_s": "{}Std {}Min {}Sek",
        "time_m_s": "{}Min {}Sek",
        "time_s": "{}Sek"
    }
}

class LanguageManager:
    FILE_NAME = "lang.json"
    
    def __init__(self, selected_lang="auto"):
        self.data = {}
        self.load_or_create()
        self.current_lang = self.detect_lang(selected_lang)

    def load_or_create(self):
        if not os.path.exists(self.FILE_NAME):
            self.data = DEFAULT_LANG_DATA
            self.save_lang_file()
        else:
            try:
                with open(self.FILE_NAME, 'r', encoding='utf-8') as f:
                    disk_data = json.load(f)
                
                # Автоматическое слияние новых ключей из DEFAULT_LANG_DATA в файл на диске
                updated = False
                for lang_code, keys_dict in DEFAULT_LANG_DATA.items():
                    if lang_code not in disk_data:
                        disk_data[lang_code] = keys_dict
                        updated = True
                    else:
                        for k, v in keys_dict.items():
                            if k not in disk_data[lang_code]:
                                disk_data[lang_code][k] = v
                                updated = True
                
                self.data = disk_data
                if updated:
                    self.save_lang_file()
            except Exception:
                self.data = DEFAULT_LANG_DATA
                self.save_lang_file()

    def save_lang_file(self):
        try:
            with open(self.FILE_NAME, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def set_language(self, lang_code):
        self.current_lang = self.detect_lang(lang_code)

    def detect_lang(self, chosen):
        if chosen in ["ru", "en", "fa", "es", "de"]:
            return chosen
        sys_lang = QLocale.system().name().split('_')[0].lower()
        if sys_lang in ["ru", "fa", "es", "de"]:
            return sys_lang
        return "en"

    def tr(self, key):
        return self.data.get(self.current_lang, {}).get(key, DEFAULT_LANG_DATA["ru"].get(key, key))

# --- Настройки ---
class Settings:
    CONFIG_FILE = "pkg_extractor_config.json"
    
    def __init__(self):
        self.games_dir = ""
        self.dlc_dir = ""
        self.pkg_extractor_path = auto_detect_pkg_extractor()
        self.dlc_keyword = "dlc"
        self.extract_dlc_to_game_id = True
        self.last_folder = ""
        self.theme = "dark"
        self.language = "auto"
        self.load()
    
    def load(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.games_dir = data.get('games_dir', "")
                    self.dlc_dir = data.get('dlc_dir', "")
                    
                    config_extractor = data.get('pkg_extractor_path', "")
                    if config_extractor and os.path.exists(config_extractor) and Path(config_extractor).name.lower() == "pkg_extractor.exe":
                        self.pkg_extractor_path = config_extractor
                    else:
                        self.pkg_extractor_path = auto_detect_pkg_extractor()
                        
                    self.dlc_keyword = data.get('dlc_keyword', "dlc")
                    self.extract_dlc_to_game_id = data.get('extract_dlc_to_game_id', True)
                    self.last_folder = data.get('last_folder', "")
                    self.theme = data.get('theme', "dark")
                    self.language = data.get('language', "auto")
            except Exception:
                pass
    
    def save(self):
        data = {
            'games_dir': self.games_dir,
            'dlc_dir': self.dlc_dir,
            'pkg_extractor_path': self.pkg_extractor_path,
            'dlc_keyword': self.dlc_keyword,
            'extract_dlc_to_game_id': self.extract_dlc_to_game_id,
            'last_folder': self.last_folder,
            'theme': self.theme,
            'language': self.language
        }
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

class PkgFileInfo:
    def __init__(self, path, is_dlc=False, game_id=None):
        self.path = path
        self.is_dlc = is_dlc
        self.game_id = game_id
        self.size = path.stat().st_size if path.exists() else 0
        self.name = path.name
        self.pkg_type = "game"
        self.dest_folder = None
        self.dest_path = None

# --- Поток распаковки ---
class ExtractWorker(QThread):
    log_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    file_progress = pyqtSignal(str, int)
    status_update = pyqtSignal(str)
    finished_summary = pyqtSignal(float, float, str, str)

    def __init__(self, file_mapping, extractor_path, total_size, games_dir, dlc_dir, lang_mgr):
        super().__init__()
        self.file_mapping = file_mapping
        self.extractor_path = extractor_path
        self.total_size = float(total_size)
        self.games_dir = games_dir
        self.dlc_dir = dlc_dir
        self.lang_mgr = lang_mgr
        self._is_cancelled = False
        self.completed_bytes = 0.0

    def run(self):
        start_time = time.time()
        total_files = len(self.file_mapping)
        tr = self.lang_mgr.tr
        is_en = (self.lang_mgr.current_lang != "ru")
        
        for i, (pkg_path, dest_dir, pkg_name, is_dlc) in enumerate(self.file_mapping):
            if self._is_cancelled:
                self.log_update.emit(tr("log_cancelled"))
                break

            os.makedirs(dest_dir, exist_ok=True)
            temp_prefix = "_temp_dlc_" if is_dlc else "_temp_"
            extract_path = Path(dest_dir) / f"{temp_prefix}{Path(pkg_name).stem}"
            os.makedirs(extract_path, exist_ok=True)

            self.log_update.emit(tr("log_extracting").format(i + 1, total_files, pkg_name))
            
            success = self.execute_extraction([self.extractor_path, str(pkg_path), str(extract_path)], extract_path, pkg_path)
            
            if not success and not self._is_cancelled:
                self.log_update.emit(tr("log_try_fake"))
                success = self.execute_extraction([self.extractor_path, str(pkg_path), str(extract_path), "fake"], extract_path, pkg_path)

            if success:
                self.log_update.emit(tr("log_extract_success").format(pkg_name))
                self.log_update.emit(tr("log_merging").format(dest_dir))
                try:
                    self.merge_folders(extract_path, Path(dest_dir))
                    if extract_path.exists():
                        shutil.rmtree(extract_path, ignore_errors=True)
                except Exception as e:
                    self.log_update.emit(tr("log_merge_error").format(e))
            else:
                if not self._is_cancelled:
                    self.log_update.emit(tr("log_extract_fail").format(pkg_name))

            self.completed_bytes += float(pkg_path.stat().st_size)
            self.file_progress.emit(pkg_name, i + 1)

        elapsed_sec = time.time() - start_time
        
        g_free = format_size(shutil.disk_usage(self.games_dir).free, is_en) if os.path.exists(self.games_dir) else "N/A"
        d_free = format_size(shutil.disk_usage(self.dlc_dir).free, is_en) if os.path.exists(self.dlc_dir) else "N/A"

        self.finished_summary.emit(elapsed_sec, self.completed_bytes, g_free, d_free)

    def execute_extraction(self, cmd, temp_dir, pkg_path):
        tr = self.lang_mgr.tr
        is_en = (self.lang_mgr.current_lang != "ru")

        if Path(self.extractor_path).name.lower() != "pkg_extractor.exe" or not os.path.exists(self.extractor_path):
            self.log_update.emit(tr("log_crit_error").format(self.extractor_path))
            return False

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE, 
                text=True,
                creationflags=creation_flags
            )
            pkg_size = float(pkg_path.stat().st_size)
            
            while process.poll() is None:
                if self._is_cancelled:
                    process.terminate()
                    return False
                
                current_temp_bytes = float(get_dir_size_fast(temp_dir))
                current_total = self.completed_bytes + min(current_temp_bytes, pkg_size)
                
                if self.total_size > 0:
                    percentage = int((current_total / self.total_size) * 100)
                    percentage = min(percentage, 99)
                    self.progress_update.emit(percentage)
                    self.status_update.emit(
                        tr("status_extracted").format(format_size(current_total, is_en), format_size(self.total_size, is_en), percentage)
                    )
                time.sleep(0.25)

            return process.returncode == 0
        except Exception as e:
            self.log_update.emit(tr("log_crit_error").format(e))
            return False

    def merge_folders(self, source, dest):
        source = Path(source)
        dest = Path(dest)
        content = list(source.iterdir())
        
        if len(content) == 1 and content[0].is_dir():
            inner_name = content[0].name.upper()
            if re.search(r'CUSA\d{5}', inner_name) or 'PATCH' in inner_name:
                source = content[0]
        
        for item in source.iterdir():
            dest_item = dest / item.name
            if item.is_dir():
                if dest_item.exists():
                    self.merge_folders(item, dest_item)
                else:
                    shutil.move(str(item), str(dest_item))
            else:
                if dest_item.exists():
                    dest_item.unlink()
                shutil.move(str(item), str(dest_item))

    def cancel(self):
        self._is_cancelled = True

# --- Диалог ввода CUSA ID ---
class GameIdDialog(QDialog):
    def __init__(self, context_name, lang_mgr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CUSA ID")
        self.setModal(True)
        self.resize(380, 130)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Context: {context_name}"))
        layout.addWidget(QLabel(lang_mgr.tr("msg_enter_id")))
        
        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("CUSAXXXXX")
        layout.addWidget(self.id_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_game_id(self):
        return self.id_edit.text().strip().upper()

# --- Главное окно приложения ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

        self.settings = Settings()
        self.lang_mgr = LanguageManager(self.settings.language)
        
        self.setGeometry(120, 120, 1150, 680)
        self.setAcceptDrops(True)
        
        self.pkg_files = []
        self.file_mapping = []
        self.worker = None
        self.total_size = 0.0
        
        self.init_ui()
        self.apply_theme(self.settings.theme)
        self.retranslate_ui()
        self.check_settings()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. Настройки путей
        self.paths_group = QGroupBox()
        paths_layout = QGridLayout(self.paths_group)
        paths_layout.setContentsMargins(6, 4, 6, 4)
        paths_layout.setSpacing(4)

        self.lbl_games = QLabel()
        paths_layout.addWidget(self.lbl_games, 0, 0)
        self.games_edit = QLineEdit(self.settings.games_dir)
        self.games_edit.setReadOnly(True)
        paths_layout.addWidget(self.games_edit, 0, 1)
        self.btn_browse_g = QPushButton()
        self.btn_browse_g.clicked.connect(lambda: self.browse_folder(self.games_edit, "games"))
        paths_layout.addWidget(self.btn_browse_g, 0, 2)

        self.lbl_extractor = QLabel()
        paths_layout.addWidget(self.lbl_extractor, 0, 3)
        self.extractor_edit = QLineEdit(self.settings.pkg_extractor_path)
        self.extractor_edit.setReadOnly(True)
        paths_layout.addWidget(self.extractor_edit, 0, 4)
        self.btn_browse_e = QPushButton()
        self.btn_browse_e.clicked.connect(self.browse_extractor)
        paths_layout.addWidget(self.btn_browse_e, 0, 5)

        self.lbl_dlc = QLabel()
        paths_layout.addWidget(self.lbl_dlc, 1, 0)
        self.dlc_edit = QLineEdit(self.settings.dlc_dir)
        self.dlc_edit.setReadOnly(True)
        paths_layout.addWidget(self.dlc_edit, 1, 1)
        self.btn_browse_d = QPushButton()
        self.btn_browse_d.clicked.connect(lambda: self.browse_folder(self.dlc_edit, "dlc"))
        paths_layout.addWidget(self.btn_browse_d, 1, 2)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(4)

        self.theme_btn = QPushButton()
        self.theme_btn.clicked.connect(self.toggle_theme)
        ctrl_layout.addWidget(self.theme_btn)

        # Выпадающий список 5 языков + Auto
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "Auto", 
            "Русский (ru)", 
            "English (en)", 
            "فارسی (fa)", 
            "Español (es)", 
            "Deutsch (de)"
        ])
        lang_map = {"auto": 0, "ru": 1, "en": 2, "fa": 3, "es": 4, "de": 5}
        self.lang_combo.setCurrentIndex(lang_map.get(self.settings.language, 0))
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        ctrl_layout.addWidget(self.lang_combo)

        paths_layout.addLayout(ctrl_layout, 1, 3, 1, 3)
        main_layout.addWidget(self.paths_group)

        # 2. Кнопки действия
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)
        
        self.add_files_btn = QPushButton()
        self.add_files_btn.clicked.connect(self.add_files)
        action_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton()
        self.add_folder_btn.clicked.connect(self.add_folder)
        action_layout.addWidget(self.add_folder_btn)

        self.clear_btn = QPushButton()
        self.clear_btn.clicked.connect(self.clear_list)
        action_layout.addWidget(self.clear_btn)

        action_layout.addStretch()
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet("color: #888888;")
        action_layout.addWidget(self.hint_label)

        main_layout.addLayout(action_layout)

        # 3. Разделитель (Таблица 60% / Лог 40%)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        table_container = QWidget()
        tbl_layout = QVBoxLayout(table_container)
        tbl_layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        tbl_layout.addWidget(self.table)
        self.splitter.addWidget(table_container)

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(2)

        log_header_layout = QHBoxLayout()
        log_header_layout.setContentsMargins(0, 0, 0, 0)
        self.log_title_lbl = QLabel()
        log_header_layout.addWidget(self.log_title_lbl)
        log_header_layout.addStretch()

        self.btn_clear_log = QPushButton()
        self.btn_clear_log.clicked.connect(self.log_text_clear_action)
        log_header_layout.addWidget(self.btn_clear_log)

        log_layout.addLayout(log_header_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 8))
        log_layout.addWidget(self.log_text)
        
        self.splitter.addWidget(log_container)
        
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setSizes([600, 400])
        main_layout.addWidget(self.splitter, 1)

        # 4. Панель статуса
        bottom_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumWidth(200)
        bottom_layout.addWidget(self.progress_bar)

        self.status_label = QLabel()
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()

        self.start_button = QPushButton()
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_extraction)
        bottom_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton()
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_extraction)
        bottom_layout.addWidget(self.cancel_button)

        main_layout.addLayout(bottom_layout)

    def log_text_clear_action(self):
        self.log_text.clear()

    # --- Динамический мгновенный переперевод всего UI и логов ---
    def retranslate_ui(self):
        tr = self.lang_mgr.tr
        self.setWindowTitle(tr("title"))
        self.paths_group.setTitle(tr("paths_group"))
        self.lbl_games.setText(tr("games_dir"))
        self.lbl_dlc.setText(tr("dlc_dir"))
        self.lbl_extractor.setText(tr("extractor_path"))
        
        self.btn_browse_g.setText(tr("browse"))
        self.btn_browse_d.setText(tr("browse"))
        self.btn_browse_e.setText(tr("browse"))

        theme_keys = {"dark": "theme_dark", "light": "theme_light"}
        self.theme_btn.setText(tr(theme_keys.get(self.settings.theme, "theme_dark")))

        auto_detected = self.lang_mgr.detect_lang("auto")
        auto_label = f"{tr('lang_auto')} ({auto_detected})"
        self.lang_combo.setItemText(0, auto_label)

        self.add_files_btn.setText(f"📁 {tr('add_files')}")
        self.add_folder_btn.setText(f"📂 {tr('add_folder')}")
        self.clear_btn.setText(f"🗑️ {tr('clear_list')}")
        self.hint_label.setText(f"⬇ {tr('drop_hint')}")

        self.table.setHorizontalHeaderLabels([
            tr("table_file"), tr("table_type"), tr("table_id"),
            tr("table_size"), tr("table_dest"), tr("table_status")
        ])

        self.log_title_lbl.setText(f"📝 {tr('log_title')}")
        self.btn_clear_log.setText(tr("clear_log"))
        
        self.start_button.setText(tr("start_btn"))
        self.cancel_button.setText(tr("cancel_btn"))

        self.update_status_style()

        if not self.worker or not self.worker.isRunning():
            self.check_settings()

        for row in range(self.table.rowCount()):
            if row < len(self.pkg_files):
                pkg = self.pkg_files[row]
                if pkg.pkg_type == "dlc":
                    type_str = tr("type_dlc")
                elif pkg.pkg_type == "update":
                    type_str = tr("type_patch")
                else:
                    type_str = tr("type_game")
                
                type_item = QTableWidgetItem(type_str)
                self.apply_cell_type_color(type_item, pkg)
                self.table.setItem(row, 1, type_item)

        # Мгновенный переперевод уже имеющегося лога в реальном времени!
        if self.pkg_files:
            self.update_log_summary()

    def update_log_summary(self):
        """Мгновенно обновляет лог пакета на активном языке"""
        if not self.pkg_files:
            return

        tr = self.lang_mgr.tr
        is_en = (self.lang_mgr.current_lang != "ru")

        games_dict = {}
        for pkg in self.pkg_files:
            games_dict.setdefault(pkg.game_id, []).append(pkg)

        self.log_text.clear()
        self.log_text.append(tr("log_pkg_updated").format(len(self.pkg_files), len(games_dict)))
        for g_id, pkgs in games_dict.items():
            g_count = sum(1 for p in pkgs if p.pkg_type == "game")
            u_count = sum(1 for p in pkgs if p.pkg_type == "update")
            d_count = sum(1 for p in pkgs if p.pkg_type == "dlc")
            g_size = sum(p.size for p in pkgs)
            
            self.log_text.append(tr("log_game_stat").format(g_id, g_count, u_count, d_count))
            self.log_text.append(tr("log_game_size").format(format_size(g_size, is_en)))

        self.log_text.append("\n" + tr("log_total_size").format(format_size(self.total_size, is_en)))

        _, space_msgs, _ = check_smart_disk_space(self.settings.games_dir, self.settings.dlc_dir, self.total_size, self.lang_mgr)
        for msg in space_msgs:
            self.log_text.append(msg)

    def update_status_style(self):
        if self.settings.theme == "dark":
            self.status_label.setStyleSheet("font-weight: bold; color: #66bb6a;")
        else:
            self.status_label.setStyleSheet("font-weight: bold; color: #2e7d32;")

    def apply_cell_type_color(self, item, pkg):
        is_dark = (self.settings.theme == "dark")
        if pkg.pkg_type == "dlc":
            if is_dark:
                item.setBackground(QColor(120, 40, 140, 110))
                item.setForeground(QColor(235, 190, 255))
            else:
                item.setBackground(QColor(225, 190, 231, 200))
                item.setForeground(QColor(74, 20, 140))
        elif pkg.pkg_type == "update":
            if is_dark:
                item.setBackground(QColor(160, 90, 0, 110))
                item.setForeground(QColor(255, 210, 140))
            else:
                item.setBackground(QColor(255, 224, 178, 200))
                item.setForeground(QColor(230, 81, 0))
        else:  # game
            if is_dark:
                item.setBackground(QColor(20, 100, 160, 110))
                item.setForeground(QColor(150, 220, 255))
            else:
                item.setBackground(QColor(187, 222, 251, 200))
                item.setForeground(QColor(13, 71, 161))

    def apply_theme(self, theme_mode):
        app = QApplication.instance()
        app.setStyle("Fusion")
        p = QPalette()
        if theme_mode == "dark":
            p.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
            p.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
            p.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
            p.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
            p.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        else:  # light
            p.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            p.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
            p.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            p.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
            p.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
            p.setColor(QPalette.ColorRole.Button, QColor(230, 230, 230))
            p.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
            p.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
            p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        app.setPalette(p)

    def toggle_theme(self):
        new_mode = "light" if self.settings.theme == "dark" else "dark"
        self.settings.theme = new_mode
        self.settings.save()
        self.apply_theme(new_mode)
        self.retranslate_ui()

    def on_lang_changed(self, index):
        langs = ["auto", "ru", "en", "fa", "es", "de"]
        selected_lang = langs[index] if index < len(langs) else "auto"
        self.settings.language = selected_lang
        self.settings.save()
        self.lang_mgr.set_language(selected_lang)
        self.retranslate_ui()

    def check_settings(self):
        if not self.settings.games_dir or not self.settings.dlc_dir:
            self.status_label.setText(self.lang_mgr.tr("paths_group"))
            self.start_button.setEnabled(False)
            return False

        extractor_path = Path(self.settings.pkg_extractor_path)
        
        is_valid_extractor = (
            extractor_path.exists() and 
            extractor_path.name.lower() == "pkg_extractor.exe" and
            str(extractor_path.resolve()) != str(Path(sys.executable).resolve())
        )

        if not is_valid_extractor:
            auto_path = auto_detect_pkg_extractor()
            if Path(auto_path).exists() and Path(auto_path).name.lower() == "pkg_extractor.exe":
                self.settings.pkg_extractor_path = auto_path
                self.extractor_edit.setText(auto_path)
                self.settings.save()
                is_valid_extractor = True

        if not is_valid_extractor:
            self.status_label.setText(self.lang_mgr.tr("msg_no_extractor"))
            self.start_button.setEnabled(False)
            return False

        if self.pkg_files:
            space_ok, _, _ = check_smart_disk_space(self.settings.games_dir, self.settings.dlc_dir, self.total_size, self.lang_mgr)
            if space_ok:
                self.start_button.setEnabled(True)
                self.status_label.setText(self.lang_mgr.tr("status_ready_files").format(len(self.pkg_files)))
            else:
                self.start_button.setEnabled(False)
                self.status_label.setText(self.lang_mgr.tr("msg_no_space"))
        else:
            self.status_label.setText(self.lang_mgr.tr("ready"))
            self.start_button.setEnabled(False)

        return True

    def browse_folder(self, line_edit, folder_type):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.settings.last_folder)
        if folder:
            line_edit.setText(folder)
            if folder_type == "games":
                self.settings.games_dir = folder
            elif folder_type == "dlc":
                self.settings.dlc_dir = folder
            self.settings.save()
            self.check_settings()

    def browse_extractor(self):
        file, _ = QFileDialog.getOpenFileName(self, "pkg_extractor.exe", "", "Executable Files (*.exe)")
        if file:
            if Path(file).name.lower() != "pkg_extractor.exe":
                self.log_text.append(f"❌ {self.lang_mgr.tr('msg_no_extractor')}")
                return
            self.extractor_edit.setText(file)
            self.settings.pkg_extractor_path = file
            self.settings.save()
            self.check_settings()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PKG Files", self.settings.last_folder, "PKG Files (*.pkg)")
        if files:
            self.settings.last_folder = str(Path(files[0]).parent)
            self.settings.save()
            self.process_pkg_files([Path(f) for f in files])

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Folder with PKG", self.settings.last_folder)
        if folder:
            self.settings.last_folder = folder
            self.settings.save()
            pkgs = list(Path(folder).rglob('*.pkg'))
            if pkgs:
                self.process_pkg_files(pkgs)

    def clear_list(self):
        self.pkg_files = []
        self.table.setRowCount(0)
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.check_settings()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        pkgs = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir():
                pkgs.extend(path.rglob('*.pkg'))
            elif path.is_file() and path.suffix.lower() == '.pkg':
                pkgs.append(path)
        if pkgs:
            self.process_pkg_files(pkgs)

    def process_pkg_files(self, incoming_pkg_files):
        tr = self.lang_mgr.tr
        is_en = (self.lang_mgr.current_lang != "ru")

        existing_paths = {p.path.resolve() for p in self.pkg_files}
        new_paths = [p for p in incoming_pkg_files if p.resolve() not in existing_paths]

        if not new_paths and self.pkg_files:
            self.log_text.append(tr("log_already_exists"))
            return

        all_pkg_paths = [p.path for p in self.pkg_files] + new_paths
        all_pkg_paths.sort()

        pkg_objects = []
        for pkg_path in all_pkg_paths:
            name_lower = pkg_path.name.lower()
            is_dlc_flag = self.settings.dlc_keyword.lower() in str(pkg_path.parent).lower()
            if not is_dlc_flag:
                for kw in ['point', 'bundle', 'vanity', 'fighter', 'kumite', 'starter', 'premium', 'rainbows', 'unicorns']:
                    if kw in name_lower:
                        is_dlc_flag = True
                        break
            
            cusa_id = find_cusa_for_file(pkg_path)
            info = PkgFileInfo(pkg_path, is_dlc=is_dlc_flag, game_id=cusa_id)
            info.pkg_type = classify_pkg_type(pkg_path, is_dlc_flag)
            pkg_objects.append(info)

        dir_groups = {}
        for p in pkg_objects:
            dir_groups.setdefault(str(p.path.parent), []).append(p)

        for dir_path, pkgs_in_dir in dir_groups.items():
            known_ids = {p.game_id for p in pkgs_in_dir if p.game_id is not None}
            
            if not known_ids:
                try:
                    for f in os.listdir(dir_path):
                        match = re.search(r'CUSA\d{5}', f, re.IGNORECASE)
                        if match:
                            known_ids.add(match.group(0).upper())
                except Exception:
                    pass

            if len(known_ids) == 1:
                single_id = next(iter(known_ids))
                for p in pkgs_in_dir:
                    if p.game_id is None:
                        p.game_id = single_id

            unknown_in_dir = [p for p in pkgs_in_dir if p.game_id is None]
            if unknown_in_dir:
                context_name = Path(dir_path).name or unknown_in_dir[0].name
                dlg = GameIdDialog(context_name, self.lang_mgr, self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    user_id = dlg.get_game_id()
                    if user_id:
                        for p in unknown_in_dir:
                            p.game_id = user_id
                    else:
                        self.log_text.append(tr("log_group_skipped").format(context_name))
                else:
                    self.log_text.append(tr("log_id_cancelled"))

        self.pkg_files = [p for p in pkg_objects if p.game_id is not None]
        if not self.pkg_files:
            return

        self.table.setRowCount(len(self.pkg_files))
        self.total_size = sum(p.size for p in self.pkg_files)

        games_dict = {}
        for pkg in self.pkg_files:
            if pkg.pkg_type == "dlc":
                dest = Path(self.settings.dlc_dir) / pkg.game_id
                pkg.dest_folder = f"_DLC\\{pkg.game_id}"
            else:
                dest = Path(self.settings.games_dir) / pkg.game_id
                pkg.dest_folder = f"Games\\{pkg.game_id}"
            pkg.dest_path = str(dest)

            games_dict.setdefault(pkg.game_id, []).append(pkg)

        for i, pkg in enumerate(self.pkg_files):
            self.table.setItem(i, 0, QTableWidgetItem(pkg.name))
            
            if pkg.pkg_type == "dlc":
                type_str = tr("type_dlc")
            elif pkg.pkg_type == "update":
                type_str = tr("type_patch")
            else:
                type_str = tr("type_game")

            type_item = QTableWidgetItem(type_str)
            self.apply_cell_type_color(type_item, pkg)
            self.table.setItem(i, 1, type_item)

            self.table.setItem(i, 2, QTableWidgetItem(pkg.game_id))
            self.table.setItem(i, 3, QTableWidgetItem(format_size(pkg.size, is_en)))
            self.table.setItem(i, 4, QTableWidgetItem(pkg.dest_folder))
            self.table.setItem(i, 5, QTableWidgetItem(tr("status_waiting")))

        self.update_log_summary()
        self.check_settings()

    def start_extraction(self):
        if not self.pkg_files:
            return
            
        if not self.check_settings():
            return

        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.file_mapping = [(p.path, p.dest_path, p.name, p.pkg_type == "dlc") for p in self.pkg_files]
        self.worker = ExtractWorker(
            self.file_mapping, 
            self.settings.pkg_extractor_path, 
            self.total_size,
            self.settings.games_dir,
            self.settings.dlc_dir,
            self.lang_mgr
        )
        self.worker.log_update.connect(self.log_text.append)
        self.worker.progress_update.connect(self.progress_bar.setValue)
        self.worker.file_progress.connect(self.update_file_status)
        self.worker.status_update.connect(self.status_label.setText)
        self.worker.finished_summary.connect(self.on_extraction_finished)
        self.worker.start()

    def update_file_status(self, file_name, file_number):
        tr = self.lang_mgr.tr
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == file_name:
                self.table.setItem(row, 5, QTableWidgetItem(f"✅ {tr('status_done')} ({file_number}/{len(self.pkg_files)})"))

    def cancel_extraction(self):
        if self.worker:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)

    def on_extraction_finished(self, elapsed_sec, total_bytes, games_free, dlc_free):
        tr = self.lang_mgr.tr
        is_en = (self.lang_mgr.current_lang != "ru")

        self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText(tr("ready"))
        
        mins, secs = divmod(int(elapsed_sec), 60)
        hours, mins = divmod(mins, 60)
        
        if hours > 0:
            time_str = tr("time_h_m_s").format(hours, mins, secs)
        elif mins > 0:
            time_str = tr("time_m_s").format(mins, secs)
        else:
            time_str = tr("time_s").format(secs)

        self.log_text.append(tr("log_finished_success"))
        self.log_text.append(tr("log_elapsed_time").format(time_str))
        self.log_text.append(tr("log_extracted_volume").format(format_size(total_bytes, is_en)))
        
        _, _, is_same_drive = check_smart_disk_space(self.settings.games_dir, self.settings.dlc_dir, 0, self.lang_mgr)
        if is_same_drive:
            self.log_text.append(tr("log_free_space_single").format(games_free))
        else:
            self.log_text.append(tr("log_free_space_multi"))
            self.log_text.append(f"   • Games: {games_free}")
            self.log_text.append(f"   • DLC: {dlc_free}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
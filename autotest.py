import os
import csv
from datetime import datetime
from metadata_parser import MetaDataParser

# Расширения файлов по типу
PHOTO_EXTS = ['.jpg', '.jpeg', '.png', '.heic', '.heif', '.tif', '.tiff', '.dng', '.raw', '.nef', '.cr2', '.arw']
VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
VIDEO360_EXTS = ['.insv']

# Путь к папке с тестовыми файлами
SAMPLES_DIR = 'samples'

# Имена выходных файлов
CSV_FILENAME = 'results.csv'
LOG_FILENAME = 'log.txt'

def run_autotest(timezone='Europe/Moscow'):
    # Инициализация парсера с нужной временной зоной
    parser = MetaDataParser(timezone=timezone)

    # Проверка наличия папки samples
    if not os.path.exists(SAMPLES_DIR):
        print(f"❌ Папка '{SAMPLES_DIR}' не найдена.")
        return

    # Получение списка файлов в папке
    files = os.listdir(SAMPLES_DIR)
    if not files:
        print(f"📂 Папка '{SAMPLES_DIR}' пуста.")
        return

    results = []

    # Очистка предыдущих логов и таблицы
    open(LOG_FILENAME, 'w').close()
    open(CSV_FILENAME, 'w').close()

    print(f"🔍 Анализируем {len(files)} файл(ов)...\n")

    for file_name in files:
        file_path = os.path.join(SAMPLES_DIR, file_name)
        extension = os.path.splitext(file_name)[1].lower()
        dt = None
        media_type = "Unknown"
        method_used = "None"

        print(f"📁 Файл: {file_name}")

        # Открываем лог для добавления строк
        with open(LOG_FILENAME, 'a') as log:
            try:
                # Определяем тип файла и парсим дату
                if extension in PHOTO_EXTS:
                    dt = parser.get_photo_exif(file_path)
                    media_type = "Photo"
                    method_used = "EXIF/RAW/Fallback"
                elif extension in VIDEO_EXTS:
                    dt = parser.get_video_exif(file_path)
                    media_type = "Video"
                    method_used = "FFPROBE/Fallback"
                elif extension in VIDEO360_EXTS:
                    dt = parser.get_video360_exif(file_path)
                    media_type = "Video360"
                    method_used = "FFPROBE/Fallback"
                else:
                    # Если формат не поддерживается
                    print("⚠️ Формат не поддерживается.")
                    log.write(f"[{file_name}] Unsupported format\n")
                    continue

                # Логируем найденную дату
                if dt:
                    print(f"📅 Дата создания: {dt}")
                    log.write(f"[{file_name}] {media_type} | OK | {dt}\n")
                else:
                    # Если EXIF отсутствует — берём дату изменения файла
                    fallback = datetime.fromtimestamp(os.path.getmtime(file_path))
                    print(f"📅 EXIF не найден. Время по файлу: {fallback}")
                    log.write(f"[{file_name}] {media_type} | No EXIF | fallback time {fallback}\n")
                    dt = fallback

            except Exception as e:
                # Если произошла ошибка — логируем её
                print(f"❌ Ошибка при анализе: {e}")
                log.write(f"[{file_name}] ERROR: {e}\n")

        # Добавляем результат в итоговую таблицу
        results.append({
            'Filename': file_name,
            'Type': media_type,
            'Date': dt,
            'Method': method_used
        })

        print("-" * 40)

    # Сохраняем результаты в CSV-таблицу
    with open(CSV_FILENAME, 'w', newline='') as csvfile:
        fieldnames = ['Filename', 'Type', 'Date', 'Method']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"\n📄 Результаты сохранены в {CSV_FILENAME}")
    print(f"📝 Лог ошибок — {LOG_FILENAME}")
import subprocess
import json
import pytz
from datetime import datetime
from PIL import Image
from pillow_heif import register_heif_opener  # Поддержка HEIC/HEIF
import rawpy  # Для обработки RAW-файлов
import os
import shutil


class MetaDataParser:
    # Ключи EXIF, где может храниться дата съёмки
    PHOTO_EXIF_KEYS = [306, 36867, 36868]  # DateTime, DateTimeOriginal, DateTimeDigitized

    # Поддерживаемые расширения изображений
    SUPPORTED_IMAGE_EXTS = ['.jpg', '.jpeg', '.heic', '.heif', '.png', '.tif', '.tiff']

    # Поддерживаемые RAW форматы
    SUPPORTED_RAW_EXTS = ['.dng', '.raw', '.nef', '.cr2', '.arw']

    # Ключи EXIF для видеофайлов
    VIDEO_EXIF_KEYS = ['creation_time', 'com.apple.quicktime.creationdate']

    def __init__(self, timezone='UTC'):
        # Установка временной зоны
        self.timezone = pytz.timezone(timezone)
        # Регистрация поддержки HEIC/HEIF
        register_heif_opener()
        # Поиск пути к ffprobe
        self.ffprobe_path = self.find_ffprobe()

    def find_ffprobe(self):
        # Пытаемся найти ffprobe в системе, если не найден — используем фиксированный путь
        path = shutil.which('ffprobe')
        return path if path else '/opt/homebrew/bin/ffprobe'  # fallback путь

    def get_photo_exif(self, file_path):
        # Определяем расширение файла
        extension = os.path.splitext(file_path)[1].lower()

        try:
            # Если файл — обычное изображение
            if extension in self.SUPPORTED_IMAGE_EXTS:
                img = Image.open(file_path)
                exif_data = img.getexif()
                # Поиск даты в известных EXIF ключах
                for key in self.PHOTO_EXIF_KEYS:
                    if key in exif_data:
                        dt = datetime.strptime(exif_data[key], '%Y:%m:%d %H:%M:%S')
                        return self.timezone.localize(dt)

            # Если файл — RAW формат
            elif extension in self.SUPPORTED_RAW_EXTS:
                with rawpy.imread(file_path) as raw:
                    # Попытка получить дату из thumbnail (в RAW нет универсального EXIF)
                    try:
                        raw_exif = raw.extract_thumb()
                        if raw_exif and hasattr(raw_exif, 'datetime'):
                            dt = datetime.strptime(raw_exif.datetime, '%Y:%m:%d %H:%M:%S')
                            return self.timezone.localize(dt)
                    except Exception as e:
                        print(f"⚠️ RAW fallback не сработал: {e}")

        except Exception as e:
            print(f"❌ Error parsing photo EXIF: {e}")

        # Если EXIF не найден — fallback на дату изменения файла
        try:
            fallback_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            return self.timezone.localize(fallback_time)
        except:
            return None

    def get_video_exif(self, file_path, suppress_errors=False):
        # Основной способ — ffprobe (через subprocess)
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ]
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, text=True)
            metadata = json.loads(result.stdout)

            # Поиск даты создания в метаданных
            if 'format' in metadata and 'tags' in metadata['format']:
                tags = metadata['format']['tags']
                for key in self.VIDEO_EXIF_KEYS:
                    if key in tags:
                        timestamp = tags[key]
                        try:
                            dt = datetime.strptime(timestamp[:19], '%Y-%m-%dT%H:%M:%S')

                            # Если дата — 1970, значит EXIF повреждён или отсутствует
                            if dt.year == 1970:
                                if not suppress_errors:
                                    print(
                                        f"⚠️ {os.path.basename(file_path)}: EXIF содержит 1970 год, вероятно, дата отсутствует.")
                                raise ValueError("EXIF дата подозрительная")

                            return self.timezone.localize(dt)

                        except ValueError:
                            pass  # Пропускаем ошибки формата даты

        except subprocess.CalledProcessError:
            if not suppress_errors:
                print(f"⚠️ ffprobe не смог прочитать файл {os.path.basename(file_path)}, используется fallback")

        except Exception as e:
            if not suppress_errors:
                print(f"❌ Ошибка при анализе видео EXIF: {e}")

        # Если ничего не получилось — fallback на время изменения файла
        try:
            fallback_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            return self.timezone.localize(fallback_time)
        except:
            return None

    def get_video360_exif(self, file_path):
        # Попытка получить дату без вывода ошибок
        result = self.get_video_exif(file_path, suppress_errors=True)
        if result:
            return result

        # Если ffprobe не смог прочитать файл, используем дату изменения
        try:
            fallback_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            print(f"ℹ️ {os.path.basename(file_path)}: .insv-файл — дата взята по времени файла")
            return self.timezone.localize(fallback_time)
        except:
            return None
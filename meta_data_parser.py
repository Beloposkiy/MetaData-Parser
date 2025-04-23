def get_photo_exif(file_path):
    register_heif_opener()
    img = Image.open(file_path)
    img_exif = img.getexif()
    if img_exif:
        try:
            return datetime.strptime(img_exif[306], '%Y:%m:%d %H:%M:%S')
        except:
            return None
    else:
        return None

def get_video_exif(file_path):
    ffprobe_path = '/opt/homebrew/bin/ffprobe'
    cmd = [ffprobe_path,
           '-v', 'quiet',
           '-print_format', 'json',
           '-show_format',
           # '-show_streams',
           file_path]

    result = subprocess.run(cmd, check=True)
    return result
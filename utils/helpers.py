import uuid
import datetime
from io import BytesIO


def generate_image_id() -> str:
    return f"IMG-{uuid.uuid4().hex[:8].upper()}"


def get_current_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_file_extension(filename: str) -> str:
    return filename.split(".")[-1].lower()


def build_s3_key(folder: str, filename: str, suffix: str = "") -> str:
    ext = get_file_extension(filename)
    name_without_ext = ".".join(filename.split(".")[:-1]) if "." in filename else filename
    if suffix:
        new_filename = f"{name_without_ext}_{suffix}.{ext}"
    else:
        new_filename = filename
    return f"{folder}/{new_filename}"


def sanitize_filename(filename: str) -> str:
    filename = filename.lower()
    filename = filename.replace(" ", "_")
    return filename


def image_to_bytesio(image, fmt: str = "JPEG") -> BytesIO:
    buf = BytesIO()
    if fmt.upper() == "JPEG":
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(buf, format="JPEG", quality=95)
    elif fmt.upper() == "WEBP":
        image.save(buf, format="WEBP", quality=90)
    else:
        image.save(buf, format=fmt.upper())
    buf.seek(0)
    return buf

from io import BytesIO
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageOps

from utils.helpers import image_to_bytesio


class ImageService:
    @staticmethod
    def open_image(fileobj) -> Image.Image:
        return Image.open(fileobj)

    @staticmethod
    def get_image_info(image: Image.Image) -> dict:
        return {
            "width": image.width,
            "height": image.height,
            "format": image.format or "JPEG",
            "mode": image.mode,
        }

    @staticmethod
    def resize_image(image: Image.Image, target_width: int) -> Image.Image:
        if target_width <= 0:
            target_width = image.width
        ratio = target_width / image.width
        target_height = int(image.height * ratio)
        return image.resize((target_width, target_height), Image.LANCZOS)

    @staticmethod
    def to_grayscale(image: Image.Image) -> Image.Image:
        return ImageOps.grayscale(image).convert("RGB")

    @staticmethod
    def to_sepia(image: Image.Image) -> Image.Image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        pixels = image.load()
        width, height = image.size
        for x in range(width):
            for y in range(height):
                r, g, b = pixels[x, y]
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                pixels[x, y] = (min(tr, 255), min(tg, 255), min(tb, 255))
        return image

    @staticmethod
    def invert_colors(image: Image.Image) -> Image.Image:
        if image.mode in ("RGBA", "LA", "P"):
            rgb_image = image.convert("RGB")
            inverted = ImageOps.invert(rgb_image)
            if image.mode == "RGBA":
                inverted.putalpha(image.split()[-1])
            return inverted
        return ImageOps.invert(image)

    @staticmethod
    def add_watermark(
        image: Image.Image,
        text: str,
        position: str = "bottom-right",
        font_size: int = None,
    ) -> Image.Image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        if font_size is None:
            font_size = max(18, int(min(image.size) * 0.035))

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        margin = int(min(image.size) * 0.03)

        if position == "bottom-right":
            x = image.width - text_width - margin
            y = image.height - text_height - margin
        elif position == "bottom-left":
            x = margin
            y = image.height - text_height - margin
        elif position == "top-right":
            x = image.width - text_width - margin
            y = margin
        elif position == "top-left":
            x = margin
            y = margin
        elif position == "center":
            x = (image.width - text_width) // 2
            y = (image.height - text_height) // 2
        else:
            x = image.width - text_width - margin
            y = image.height - text_height - margin

        shadow_offset = max(1, font_size // 20)
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0, 180),
        )

        draw.text(
            (x, y),
            text,
            font=font,
            fill=(255, 255, 255, 220),
        )

        combined = Image.alpha_composite(image, overlay)
        return combined.convert("RGB")

    @staticmethod
    def convert_format(image: Image.Image, target_format: str) -> tuple:
        target_format = target_format.upper()

        if target_format == "JPEG":
            if image.mode in ("RGBA", "P", "LA"):
                image = image.convert("RGB")
            result_format = "JPEG"
            ext = "jpg"
        elif target_format == "PNG":
            if image.mode == "P":
                image = image.convert("RGBA")
            result_format = "PNG"
            ext = "png"
        elif target_format == "WEBP":
            result_format = "WEBP"
            ext = "webp"
        else:
            result_format = image.format or "JPEG"
            ext = "jpg"

        buf = image_to_bytesio(image, result_format)
        new_size = len(buf.getvalue())
        buf.seek(0)
        return image, buf, result_format, ext, new_size

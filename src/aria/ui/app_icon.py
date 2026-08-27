"""
Application icon drawn programmatically - single source shared by the Qt
taskbar/window icons and the pystray tray icon (no bundled image assets).
"""

from io import BytesIO

from PIL import Image, ImageDraw
from PyQt6.QtGui import QIcon, QPixmap

# Taskbar shows scaled-down tiles; several sizes avoid blur on high DPI.
_SIZES = (16, 24, 32, 48, 64, 128)

DEFAULT_COLOR = "#3B8ED0"


def render_icon_image(size: int = 64, color: str = DEFAULT_COLOR) -> Image.Image:
    """Render the ARIA icon (colored disc + white microphone) as a PIL image."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(x0: float, y0: float, x1: float, y1: float) -> list[float]:
        # Coordinates expressed on a 64-unit grid and scaled to any size.
        return [round(v * size / 64) for v in (x0, y0, x1, y1)]

    stroke = max(2, round(size * 3 / 64))

    draw.ellipse(box(4, 4, 60, 60), fill=color)

    mic_color = "white"
    draw.rounded_rectangle(box(24, 16, 40, 36), radius=round(size * 6 / 64), fill=mic_color)
    draw.arc(box(20, 24, 44, 48), start=0, end=180, fill=mic_color, width=stroke)
    draw.line([*box(32, 48, 32, 52)], fill=mic_color, width=stroke)
    draw.line([*box(24, 52, 40, 52)], fill=mic_color, width=stroke)

    return image


def _image_to_pixmap(image: Image.Image) -> QPixmap:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue())
    return pixmap


def create_app_icon() -> QIcon:
    """Create the ARIA window/taskbar icon in multiple resolutions."""
    icon = QIcon()
    for size in _SIZES:
        icon.addPixmap(_image_to_pixmap(render_icon_image(size)))
    return icon

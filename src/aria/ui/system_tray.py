"""
System Tray integration for ARIA.

Provides a system tray icon with context menu for controlling the app
when the main window is minimized.
"""

import threading
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from ..i18n import t


class SystemTray:
    """
    System tray icon manager.

    Provides:
    - Tray icon with status indicator
    - Right-click context menu
    - Show/hide main window
    - Start/stop subtitles
    """

    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        """
        Initialize the system tray.

        Args:
            on_show: Callback to show main window
            on_toggle: Callback to toggle subtitles (start/stop)
            on_quit: Callback to quit the application
        """
        self.on_show = on_show
        self.on_toggle = on_toggle
        self.on_quit = on_quit

        self._icon: pystray.Icon | None = None
        self._is_running = False
        self._thread: threading.Thread | None = None

    def _create_icon_image(self, color: str = "#3B8ED0") -> Image.Image:
        """
        Create tray icon image.

        Args:
            color: Icon color (indicates status)

        Returns:
            PIL Image for tray icon
        """
        # Create a simple circular icon
        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw outer circle (background)
        draw.ellipse([4, 4, size - 4, size - 4], fill=color)

        # Draw inner microphone shape
        mic_color = "white"
        # Microphone body
        draw.rounded_rectangle([24, 16, 40, 36], radius=6, fill=mic_color)
        # Microphone stand
        draw.arc([20, 24, 44, 48], start=0, end=180, fill=mic_color, width=3)
        draw.line([32, 48, 32, 52], fill=mic_color, width=3)
        draw.line([24, 52, 40, 52], fill=mic_color, width=3)

        return image

    def _create_menu(self) -> pystray.Menu:
        """Create the context menu."""
        return pystray.Menu(
            pystray.MenuItem(
                t("tray_show_settings"),
                self._on_show_click,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                t("tray_toggle_subtitles"),
                self._on_toggle_click,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                t("tray_quit"),
                self._on_quit_click,
            ),
        )

    def _on_show_click(self, icon, item) -> None:
        """Handle show window click."""
        self.on_show()

    def _on_toggle_click(self, icon, item) -> None:
        """Handle toggle subtitles click."""
        self.on_toggle()

    def _on_quit_click(self, icon, item) -> None:
        """Handle quit click."""
        self.stop()
        self.on_quit()

    def start(self) -> None:
        """Start the system tray icon."""
        if self._is_running:
            return

        self._is_running = True

        # Create icon
        self._icon = pystray.Icon(
            name="aria",
            icon=self._create_icon_image(),
            title="ARIA",
            menu=self._create_menu(),
        )

        # Run in background thread
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

        from ..logger import info

        info("SystemTray: Started")

    def stop(self) -> None:
        """Stop the system tray icon."""
        if self._icon:
            self._icon.stop()
            self._icon = None

        self._is_running = False
        from ..logger import info

        info("SystemTray: Stopped")

    def update_status(self, is_active: bool) -> None:
        """
        Update the tray icon to reflect status.

        Args:
            is_active: True if subtitles are running
        """
        if self._icon:
            color = "#00AA00" if is_active else "#3B8ED0"
            self._icon.icon = self._create_icon_image(color)
            self._icon.title = f"ARIA ({'Running' if is_active else 'Stopped'})"

    def show_notification(self, title: str, message: str) -> None:
        """
        Show a Windows notification.

        Args:
            title: Notification title
            message: Notification message
        """
        if self._icon:
            self._icon.notify(message, title)


# Quick test
if __name__ == "__main__":
    import time

    def show():
        print("Show window")

    def toggle():
        print("Toggle subtitles")

    def quit_app():
        print("Quit app")

    tray = SystemTray(on_show=show, on_toggle=toggle, on_quit=quit_app)
    tray.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tray.stop()

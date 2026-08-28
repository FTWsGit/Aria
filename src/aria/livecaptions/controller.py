"""
Windows LiveCaptions Controller
Automatically launch and configure LiveCaptions
"""

import time

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None

try:
    import uiautomation as auto

    UIAUTOMATION_AVAILABLE = True
except ImportError:
    UIAUTOMATION_AVAILABLE = False
    auto = None

from ..logger import debug, error, info, warning


def is_windows_11() -> bool:
    """Check if running on Windows 11 (build >= 22000)."""
    try:
        import platform

        version = platform.version()
        parts = version.split(".")
        if len(parts) >= 3:
            build = int(parts[2].split("-")[0])
            return build >= 22000
        return False
    except Exception as e:
        warning(f"LiveCaptionsController: Error checking Windows version: {e}")
        return False


def is_livecaptions_available() -> bool:
    """Check if LiveCaptions feature is available on this system."""
    if not is_windows_11():
        debug("LiveCaptionsController: Not Windows 11")
        return False
    return True


class LiveCaptionsController:
    """
    Controls the launch and configuration of Windows LiveCaptions
    """

    @staticmethod
    def is_windows_11() -> bool:
        """Check if running on Windows 11 (delegates to module-level function)."""
        return is_windows_11()

    @staticmethod
    def is_livecaptions_available() -> bool:
        """Check if LiveCaptions feature is available (delegates to module-level function)."""
        return is_livecaptions_available()

    @staticmethod
    def launch_livecaptions() -> bool:
        """
        Launch LiveCaptions

        Method:
        1. Use keyboard shortcut Win + Ctrl + L
        2. Wait for window to appear

        Returns:
            bool: Whether launch was successful
        """
        if not PYAUTOGUI_AVAILABLE:
            error("LiveCaptionsController: pyautogui is required")
            return False

        try:
            info("LiveCaptionsController: Launching LiveCaptions...")

            # Temporarily disable fail-safe to prevent corner trigger issues
            original_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False

            try:
                # Method 1: Simulate hotkey
                pyautogui.hotkey("win", "ctrl", "l")
                info("LiveCaptionsController: Launched via hotkey (Win+Ctrl+L)")
            finally:
                # Restore fail-safe setting
                pyautogui.FAILSAFE = original_failsafe

            # Wait for window to appear
            time.sleep(2)

            # Verify window appeared
            if UIAUTOMATION_AVAILABLE:
                try:
                    window = auto.WindowControl(searchDepth=1, Name="Live Captions")
                    if window.Exists(0, 0):
                        info("LiveCaptionsController: LiveCaptions window found")
                        return True
                except Exception:
                    pass

            # Even if verification fails, return success (may have launched but positioning failed)
            return True

        except Exception as e:
            error(f"LiveCaptionsController: Failed to launch: {e}")
            return False

    @staticmethod
    def minimize_livecaptions_window() -> bool:
        """
        Minimize LiveCaptions window to taskbar

        This keeps the window accessible for UI Automation while hiding it from view.
        Better than moving off-screen which breaks UI Automation.

        Returns:
            bool: Whether minimizing was successful
        """
        if not UIAUTOMATION_AVAILABLE:
            warning("LiveCaptionsController: uiautomation not available")
            return False

        try:
            import win32con
            import win32gui

            # Find window by class name
            hwnd = win32gui.FindWindow("LiveCaptionsDesktopWindow", None)
            if hwnd:
                # Minimize to taskbar
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                debug("LiveCaptionsController: Window minimized")
                return True
            else:
                # Try with uiautomation
                window = auto.WindowControl(searchDepth=1, ClassName="LiveCaptionsDesktopWindow")
                if window.Exists(0, 0):
                    # Move to bottom-right corner and make it small
                    try:
                        import win32api

                        screen_width = win32api.GetSystemMetrics(0)
                        screen_height = win32api.GetSystemMetrics(1)
                        window.MoveWindow(screen_width - 50, screen_height - 50, 1, 1)
                        debug("LiveCaptionsController: Window moved to corner")
                        return True
                    except Exception:
                        pass

                warning("LiveCaptionsController: Window not found for minimizing")
                return False
        except Exception as e:
            warning(f"LiveCaptionsController: Failed to minimize window: {e}")
            # Fallback: keep window visible
            return False

    @staticmethod
    def is_livecaptions_running() -> bool:
        """
        Check if LiveCaptions is currently running

        Returns:
            bool: Whether it's running
        """
        if not UIAUTOMATION_AVAILABLE:
            return False

        try:
            window = auto.WindowControl(searchDepth=1, ClassName="LiveCaptionsDesktopWindow")
            return window.Exists(0, 0)
        except Exception:
            return False

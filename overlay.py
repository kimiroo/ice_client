import sys
import ctypes
import logging
from multiprocessing import Queue, shared_memory

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QByteArray, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap

from config import *

log = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    def __init__(self, image_bytes=None):
        super().__init__()

        # Calculate coordinates for display's bottom right
        try:
            user32 = ctypes.windll.user32
            screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            coor_x = screensize[0] - WINDOW_WIDTH
            coor_y = screensize[1] - WINDOW_HEIGHT
        except Exception as e:
            log.warning(f"Error getting screen size: {e}")
            # Fallback coordinates
            coor_x = 800
            coor_y = 400

        # Set window geometry and flags for an overlay
        self.setGeometry(coor_x, coor_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Set window-wide opacity (much cleaner than per-element alpha)
        self.setWindowOpacity(GLOBAL_OPACITY / 255.0)

        # Initialize with dummy red box
        self._create_dummy_image()

        # Load initial image if provided
        if image_bytes:
            self.update_image(image_bytes)

        # Scale image
        self.image = self.image.scaled(
            WINDOW_WIDTH, WINDOW_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def _create_dummy_image(self):
        """Create a dummy red placeholder image"""
        log.debug("Creating dummy red placeholder image")
        self.image = QPixmap(1280, 720) # dummy 16:9 image
        self.image.fill(QColor(255, 30, 30))

    def update_image(self, image_bytes):
        """Update the overlay image with new image data"""
        try:
            byte_array = QByteArray(image_bytes)
            new_image = QPixmap()

            if new_image.loadFromData(byte_array):
                # Scale image
                new_image = new_image.scaled(
                    WINDOW_WIDTH, WINDOW_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                self.image = new_image
                self.update()  # Trigger repaint
                log.debug("Image updated successfully")
            else:
                log.error("Failed to load image from bytes")

        except Exception as e:
            log.error(f"Error updating image: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            # 1. Draw Image (no opacity setting needed - handled by window)
            if not self.image.isNull():
                painter.drawPixmap(0, 0, self.image)

            # 2. Draw Background Rectangle (below image area)
            background_rect_y = self.image.height()
            background_rect_height = self.height() - self.image.height()

            background_rect = QRect(0, background_rect_y, self.width(), background_rect_height)
            painter.fillRect(background_rect, BACKGROUND_COLOR)

            # 3. Draw Text using drawText (much simpler!)
            painter.setPen(FONT_COLOR)  # Set text color
            painter.setFont(QFont(FONT_FAMILY, FONT_SIZE, QFont.Weight.Bold))

            # Create text rectangle with some padding from bottom
            text_padding = 5
            text_rect = QRect(
                0,
                background_rect_y,
                self.width(),
                background_rect_height - text_padding
            )

            # Draw text centered horizontally, aligned to bottom of available space
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                TEXT_CONTENT
            )

        except Exception as e:
            log.critical(f"Error in paintEvent: {e}")
            # Draw fallback content
            painter.fillRect(self.rect(), QColor(255, 0, 0))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "ERROR")


def run_qt(image_bytes: bytes = None):
    log.debug("Starting Qt up...")

    app = QApplication()

    window = OverlayWindow(image_bytes)
    window.show()

    #QTimer.singleShot(100, update_image)

    QTimer.singleShot(WARN_DURATION * 1000, app.quit)

    app.exec()

    sys.exit()

if __name__ == '__main__':
    log.critical("This is a module. Call from the main module.")

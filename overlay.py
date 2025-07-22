import sys
import ctypes
import logging
from multiprocessing import Queue

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

        # Load image for overlay
        if image_bytes:
            byte_array = QByteArray(image_bytes)
            self.image = QPixmap()
            if not self.image.loadFromData(byte_array):
                # Failed to load from bytes, create dummy
                log.error("Failed to load image from bytes. Creating dummy placeholder...")
                self.image = QPixmap(1600, 900)
                self.image.fill(QColor(255, 30, 30))
        else:
            # No bytes provided, create dummy
            log.warning("No image bytes provided. Creating dummy placeholder...")
            self.image = QPixmap(1600, 900)
            self.image.fill(QColor(255, 30, 30))

        # Scale image once during initialization if needed (performance improvement)
        if self.image.width() > WINDOW_WIDTH or self.image.height() > WINDOW_HEIGHT:
            self.image = self.image.scaled(
                WINDOW_WIDTH, WINDOW_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

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


def run_qt(queue: Queue):
    log.debug("Starting Qt up...")

    # Get initial image data from the queue
    initial_image_bytes = None
    try:
        command = queue.get(timeout=5)
        if command['type'] == 'INIT_IMAGE' and 'data' in command:
            initial_image_bytes = command['data']
            log.debug("Received image data from queue.")
        else:
            log.error("No initial image data in first queue item or wrong type.")
    except Exception as e:
        log.critical(f"Error getting initial data from queue: {e}")

    app = QApplication()

    window = OverlayWindow(initial_image_bytes)
    window.show()

    QTimer.singleShot(WARN_DURATION * 1000, app.quit)

    app.exec()

    sys.exit()

if __name__ == '__main__':
    log.critical("This is a module. Call from the main module.")

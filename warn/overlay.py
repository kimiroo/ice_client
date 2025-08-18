import sys
import ctypes
import logging
from multiprocessing import Queue

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QByteArray, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap

from utils.config import config

log = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    def __init__(self, overlay_title: str, overlay_message: str = None):
        super().__init__()

        self.overlay_title = overlay_title
        self.overlay_message = overlay_message

        # Calculate coordinates for display's bottom right
        try:
            user32 = ctypes.windll.user32
            screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            coor_x = screensize[0] - config.window_width
            coor_y = screensize[1] - config.window_height
        except Exception as e:
            log.warning(f'Error getting screen size: {e}')
            # Fallback coordinates
            coor_x = 800
            coor_y = 400

        # Set window geometry and flags for an overlay
        self.setGeometry(coor_x, coor_y, config.window_width, config.window_height)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Set window-wide opacity (much cleaner than per-element alpha)
        self.setWindowOpacity(config.global_opacity / 255.0)

        # Initialize with dummy red box
        self._create_dummy_image()

    def _create_dummy_image(self):
        '''Create a dummy red placeholder image'''
        log.debug('Creating dummy red placeholder image')
        dummy_image = QPixmap(1280, 720) # dummy 16:9 image
        dummy_image.fill(QColor(255, 30, 30))
        self.image = dummy_image.scaled(
            config.window_width, config.window_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def update_image(self, image_bytes):
        '''Update the overlay image with new image data'''
        try:
            byte_array = QByteArray(image_bytes)
            new_image = QPixmap()

            if new_image.loadFromData(byte_array):
                # Scale image
                new_image = new_image.scaled(
                    config.window_width, config.window_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                self.image = new_image
                self.update()  # Trigger repaint
                log.debug('Image updated successfully')
            else:
                log.error('Failed to load image from bytes')

        except Exception as e:
            log.error(f'Error updating image: {e}')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        try:
            # 1. Draw Image (no opacity setting needed - handled by window)
            if not self.image.isNull():
                painter.drawPixmap(0, 0, self.image)

            # 2. Check if there is a message to draw in the image area
            if self.overlay_message:
                painter.setPen(config.font_message_color)
                painter.setFont(QFont(config.font_family, config.font_message_size, QFont.Weight.Bold))

                image_rect = QRect(0, 0, config.window_width, self.image.height())

                # Draw message in the center of the image area
                painter.drawText(
                    image_rect,
                    Qt.AlignmentFlag.AlignCenter,
                    self.overlay_message
                )

            # 3. Draw Background Rectangle (below image area)
            background_rect_y = self.image.height()
            background_rect_height = self.height() - self.image.height()

            background_rect = QRect(0, background_rect_y, self.width(), background_rect_height)
            painter.fillRect(background_rect, config.background_color)

            # 4. Draw Text using drawText (much simpler!)
            painter.setPen(config.font_title_color)  # Set text color
            painter.setFont(QFont(config.font_family, config.font_title_size, QFont.Weight.Bold))

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
                self.overlay_title
            )

        except Exception as e:
            log.critical(f'Error in paintEvent: {e}')
            # Draw fallback content
            painter.fillRect(self.rect(), QColor(255, 0, 0))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'ERROR')

def check_queue_and_update(window: OverlayWindow, image_queue: Queue):
    """
    Check the queue for new image data and update the window.
    """
    try:
        # get_nowait() checks for an item without blocking
        # This is important for not freezing the UI
        image_bytes = image_queue.get_nowait()
        window.update_image(image_bytes)
        log.debug('Received image from queue and updated window')
    except Exception:
        # Queue is empty, just continue
        pass

def run_qt(overlay_title: str, image_queue: Queue, overlay_message: str= None):
    log.debug('Starting Qt up...')

    app = QApplication()

    window = OverlayWindow(overlay_title, overlay_message)
    window.show()

    # Create a QTimer to periodically check the queue for new images
    timer = QTimer()
    timer.timeout.connect(lambda: check_queue_and_update(window, image_queue))
    timer.start(100)  # Check every 100ms

    # Set a total lifetime for the window
    lifetime_timer = QTimer()
    lifetime_timer.singleShot(config.warn_duration * 1000, app.quit)

    app.exec()

    sys.exit()

if __name__ == '__main__':
    log.critical('This is a module. Call from the main module.')

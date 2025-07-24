from PySide6.QtGui import QColor

# Home Assistant WebSocket Server IP and Port
WS_SERVER_IP = "10.5.47.10"
WS_SERVER_PORT = 8765

# Camera
RTSP_URL = "rtsp://tapo_cam:zz%6k5CWYXc0tpTSqwS*qbgYD6!$axmK@10.5.21.10:554/stream1"

# Warn Common
WARN_DURATION = 10 # in seconds

# Overlay
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 273
GLOBAL_OPACITY = 204  # Opacity value (0-255), where 255 is fully opaque
TEXT_CONTENT = "MOVEMENT DETECTED"
FONT_FAMILY = "Arial"
FONT_SIZE = 24
FONT_COLOR = QColor(255, 30, 30)  # Bright red, fully opaque
BACKGROUND_COLOR = QColor(0, 0, 0)  # Black, fully opaque

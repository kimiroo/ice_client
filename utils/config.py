import json
import logging
from PySide6.QtGui import QColor

CONFIG_PATH = 'config.json'

log = logging.getLogger(__name__)

# Warn Common
WARN_DURATION = 10 # in seconds

# Overlay
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 273
GLOBAL_OPACITY = 204  # Opacity value (0-255), where 255 is fully opaque
TEXT_CONTENT = 'MOVEMENT DETECTED'
FONT_FAMILY = 'Arial'
FONT_TITLE_SIZE = 24
FONT_TITLE_COLOR = QColor(255, 30, 30)  # Bright red
FONT_MESSAGE_SIZE = 24
FONT_MESSAGE_COLOR = QColor(0, 0, 0)  # Black
BACKGROUND_COLOR = QColor(0, 0, 0)  # Black

class Config:
    def __init__(self):
        self.ice_server_url = None
        self.client_name = None
        self.camera_frame_url = None

        self.obs_enabled = False
        self.obs_host = None
        self.obs_port = None
        self.obs_password = None

        self.kill_config = {}

        self.warn_duration = WARN_DURATION
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        self.global_opacity = GLOBAL_OPACITY
        self.font_family = FONT_FAMILY
        self.font_title_size = FONT_TITLE_SIZE
        self.font_title_color = FONT_TITLE_COLOR
        self.font_message_size = FONT_MESSAGE_SIZE
        self.font_message_color = FONT_MESSAGE_COLOR
        self.background_color = BACKGROUND_COLOR

        config_data = {}

        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

        except Exception as e:
            log.critical(f'Failed to load config file: {e}')

        try:
            self.ice_server_url = config_data['iceServerURL']
            self.client_name = config_data['clientName']
            self.camera_frame_url = config_data['cameraFrameURL']

            obs_config = config_data.get('obs', {})
            self.obs_host = obs_config.get('host', None)
            self.obs_port = obs_config.get('port', None)
            self.obs_password = obs_config.get('password', None)
            self.obs_enabled = self.obs_host is not None and self.obs_port is not None

            self.kill_config = config_data.get('kill', {})

        except Exception as e:
            log.critical(f'Failed to parse config file: {e}')

config = Config()

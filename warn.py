import logging
from multiprocessing import Process
import datetime

from config import WARN_DURATION
from overlay import run_qt
from sound import run_audio

log = logging.getLogger(__name__)

class WarnSession:
    def __init__(self):
        self.last_warned = datetime.datetime(1900,1,1,0,0,0,0)

        self.qt_process = None
        self.is_qt_running = False

        self.audio_process = None
        self.is_audio_running = False

    def start(self, image_bytes: bytes = None):


        time_diff = datetime.datetime.now() - self.last_warned

        if time_diff > datetime.timedelta(seconds=WARN_DURATION):
            log.info("Starting Warning Sequence...")
            self.last_warned = datetime.datetime.now()

            self._start_qt(image_bytes)
            self._start_audio()
        else:
            log.info("Ignoring warning...")

    def stop(self):
        log.info("Stopping Warning Sequence...")
        self._stop_qt()
        self._stop_audio()

    def _start_qt(self, image_bytes: bytes = None):
        log.debug("Starting Qt...")

        if self.qt_process or self.is_qt_running:
            log.debug('Qt already running. Killing...')
            self._stop_qt()

        # Create a new process targeting run_qt
        self.qt_process = Process(target=run_qt, args=(image_bytes,))
        self.qt_process.daemon = False

        self.qt_process.start()
        self.is_qt_running = True

    def _stop_qt(self):
        log.debug("Killing Qt...")
        self.qt_process.kill()
        self.qt_process.join(timeout=2)
        self.qt_process = None
        self.is_qt_running = False

    def _start_audio(self):
        log.debug("Starting Audio...")

        if self.audio_process or self.is_audio_running:
            log.debug('Audio already running. Killing...')
            self._stop_audio()

        # Create a new process targeting run_audio
        self.audio_process = Process(target=run_audio)
        self.audio_process.daemon = False

        self.audio_process.start()
        self.is_audio_running = True

    def _stop_audio(self):
        log.debug("Killing Audio...")
        self.audio_process.kill()
        self.audio_process.join(timeout=2)
        self.audio_process = None
        self.is_audio_running = False

if __name__ == '__main__':
    log.critical("This is a module. Call from the main module.")

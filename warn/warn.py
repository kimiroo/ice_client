import logging
from multiprocessing import Process, Queue
import datetime

from utils.config import config
from warn.overlay import run_qt
from warn.sound import run_audio

log = logging.getLogger(__name__)

class WarnSession:
    def __init__(self):
        self.current_event_text = None
        self.last_warned = datetime.datetime(1900,1,1,0,0,0,0)

        self.qt_process = None
        self.is_qt_running = False
        self.image_queue = Queue()

        self.audio_process = None
        self.is_audio_running = False

    def start(self, event_text: str,
              overlay_text: str,
              overlay_message: str = None,
              no_audio: bool = False,
              is_priority: bool = False):

        if is_priority:
            log.info(f'Priority warning \'{event_text}\' received.')
            self._stop()
        else:
            time_now = datetime.datetime.now()
            time_diff = time_now - self.last_warned
            if time_diff.total_seconds() < config.warn_duration:
                log.info(f'Ongoing warning \'{self.current_event_text}\' exists. Ignoring \'{event_text}\'')
                return

        log.debug('Starting Warning Sequence...')
        self.current_event_text = event_text
        self.last_warned = datetime.datetime.now()

        if not no_audio:
            self._start_audio()
        self._start_qt(overlay_text, overlay_message)

    def stop(self, event_text: str):
        if event_text == '_force_stop_all' or event_text == self.current_event_text:
            self._stop()
        log.info(f'Tried to dismiss non-matching event. Ignoring : given: {event_text}, current: {self.current_event_text}')
        return

    def update_image(self, image_bytes: bytes = None):
        self.image_queue.put(image_bytes)

    def _stop(self):
        log.debug('Stopping Warning Sequence...')
        self._stop_qt()
        self._stop_audio()

    def _start_qt(self, overlay_text: str, overlay_message: str = None):
        log.debug('Starting Qt...')

        if self.qt_process or self.is_qt_running:
            log.debug('Qt already running. Killing...')
            self._stop_qt()

        # Create a new process targeting run_qt
        self.qt_process = Process(target=run_qt, args=(overlay_text, self.image_queue, overlay_message))
        self.qt_process.daemon = False

        self.qt_process.start()
        self.is_qt_running = True

    def _stop_qt(self):
        log.debug('Killing Qt...')
        if self.qt_process or self.is_qt_running:
            try:
                self.qt_process.kill()
                self.qt_process.join(timeout=.1)
                self.qt_process = None
                self.is_qt_running = False
            except Exception as e:
                log.debug(f'Error killing Qt process: {e} Qt might be already dead.')
        else:
            log.debug('Qt process is not running. Nothing to kill.')

    def _start_audio(self):
        log.debug('Starting Audio...')

        if self.audio_process or self.is_audio_running:
            log.debug('Audio already running. Killing...')
            self._stop_audio()

        # Create a new process targeting run_audio
        self.audio_process = Process(target=run_audio)
        self.audio_process.daemon = False

        self.audio_process.start()
        self.is_audio_running = True

    def _stop_audio(self):
        log.debug('Killing Audio...')
        if self.audio_process or self.is_audio_running:
            try:
                self.audio_process.kill()
                self.audio_process.join(timeout=.1)
                self.audio_process = None
                self.is_audio_running = False
            except Exception as e:
                log.debug(f'Error killing Audio process: {e} Audio might be already dead.')
        else:
            log.debug('Audio process is not running. Nothing to kill.')

if __name__ == '__main__':
    log.critical('This is a module. Call from the main module.')

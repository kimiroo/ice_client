# src: https://github.com/TaylorSMarks/playsound

import datetime
import logging
from ctypes import create_unicode_buffer, windll, wintypes

from utils.config import WARN_DURATION

log = logging.getLogger(__name__)

class PlaysoundException(Exception):
    pass

def _canonicalizePath(path):
    """
    Support passing in a pathlib.Path-like object by converting to str.
    """
    import sys
    if sys.version_info[0] >= 3:
        return str(path)
    else:
        # On earlier Python versions, str is a byte string, so attempting to
        # convert a unicode string to str will fail. Leave it alone in this case.
        return path

def playsound(sound, block = True):
    sound = '"' + _canonicalizePath(sound) + '"'

    windll.winmm.mciSendStringW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.UINT, wintypes.HANDLE]
    windll.winmm.mciGetErrorStringW.argtypes = [wintypes.DWORD, wintypes.LPWSTR, wintypes.UINT]

    def winCommand(*command):
        bufLen = 600
        buf = create_unicode_buffer(bufLen)
        command = ' '.join(command)
        errorCode = int(windll.winmm.mciSendStringW(command, buf, bufLen - 1, 0))  # use widestring version of the function
        if errorCode:
            errorBuffer = create_unicode_buffer(bufLen)
            windll.winmm.mciGetErrorStringW(errorCode, errorBuffer, bufLen - 1)  # use widestring version of the function
            exceptionMessage = ('\n    Error ' + str(errorCode) + ' for command:'
                                '\n        ' + command +
                                '\n    ' + errorBuffer.value)
            log.error(exceptionMessage)
            raise PlaysoundException(exceptionMessage)
        return buf.value

    try:
        winCommand(u'open {}'.format(sound))
        winCommand(u'play {}{}'.format(sound, ' wait' if block else ''))
    finally:
        try:
            winCommand(u'close {}'.format(sound))
        except PlaysoundException:
            log.error(u'Failed to close the file: {}'.format(sound))
            # If it fails, there's nothing more that can be done...
            pass

def run_audio():
    log.debug("Starting Audio up...")

    start = datetime.datetime.now()
    while True:
        # Check for warning duration
        now = datetime.datetime.now()
        diff = now - start
        if diff >= datetime.timedelta(seconds=WARN_DURATION):
            break

        playsound('warn.wav')

if __name__ == '__main__':
    log.critical("This is a module. Call from the main module.")

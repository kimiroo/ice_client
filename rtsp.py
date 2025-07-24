import threading
import logging
import time

import cv2

log = logging.getLogger(__name__)


class RTSP:
    """OpenCV VideoCapture를 계속 열어놓고 사용하는 방식"""

    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.cap = None
        self.is_connected = False
        self.latest_frame = None
        self.lock = threading.Lock()
        self.read_thread = None
        self.running = False

    def connect(self):
        """OpenCV VideoCapture 연결"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)

            # 최적화 설정
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer (attempt)

            # Test connection and read an initial frame
            ret, frame = self.cap.read()
            if ret:
                self.is_connected = True
                self.latest_frame = frame # Store initial frame
                self.running = True
                self.read_thread = threading.Thread(target=self._read_frames_continuously, daemon=True)
                self.read_thread.start()
                log.info("OpenCV persistent connection established and read thread started")
                return True
            else:
                log.error("OpenCV connection test failed")
                return False

        except Exception as e:
            log.error(f"OpenCV connection error: {e}")
            return False

    def _read_frames_continuously(self):
        """Reads frames continuously in a separate thread."""
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
                else:
                    log.warning("Failed to read frame in continuous read thread. Attempting to reconnect...")
                    # Optional: Add re-connection logic here if stream breaks
                    time.sleep(1) # Prevent busy-waiting
                    # For simplicity, if read fails, we might stop or try to reconnect
                    # A robust solution would have more sophisticated reconnect logic.
            except Exception as e:
                log.error(f"Error in continuous frame reading thread: {e}")
                # If an error occurs, try to reset or stop
                self.running = False # Stop the thread on error
                break # Exit loop
            # Small sleep to prevent 100% CPU usage if frames are read too fast
            # Adjust based on your desired FPS and CPU usage.
            time.sleep(0.001)

    def get_frame_bytes(self, quality=85):
        """Get the latest frame as bytes."""
        if not self.is_connected or not self.cap or self.latest_frame is None:
            return None

        try:
            with self.lock:
                # Use the already updated latest_frame
                frame_to_encode = self.latest_frame

            if frame_to_encode is not None:
                # JPEG encoding
                ret, buffer = cv2.imencode('.jpg', frame_to_encode, [cv2.IMWRITE_JPEG_QUALITY, quality])
                return buffer.tobytes() if ret else None
            else:
                log.warning("No latest frame available to encode.")
                return None

        except Exception as e:
            log.error(f"Error encoding frame for output: {e}")
            return None

    def close(self):
        """Release OpenCV VideoCapture."""
        self.running = False # Signal the reading thread to stop
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=5) # Wait for the thread to finish
            if self.read_thread.is_alive():
                log.warning("Read thread did not terminate in time.")

        if self.cap:
            self.cap.release()
            self.is_connected = False
            log.info("OpenCV persistent connection closed")
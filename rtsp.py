import cv2

URL = "rtsp://10.5.38.100:555/live"

class Rtsp:
    def __init__(self, rtsp_url: str = None):
        self.url = rtsp_url if rtsp_url else URL
        self.rtsp = cv2.VideoCapture(self.url)

    def capture(self):

        if not self.rtsp.isOpened():
            print(f"Error: Could not open RTSP stream at {self.url}.")
            return None

        # Read a single frame
        ret, frame = self.rtsp.read()

        if ret:
            print("Frame successfully captured. Encoding to Base64...")
            # Encode the OpenCV frame to JPEG format in memory
            # Quality can be adjusted (0-100), e.g., 90 for 90% quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
            ret_encode, buffer = cv2.imencode('.jpg', frame, encode_param)

            if not ret_encode:
                print("Error: Could not encode captured frame to JPEG buffer.")
                return None

            # Convert the buffer (numpy array of bytes) to a standard bytes object
            return buffer.tobytes()
        else:
            print(f"Error: Could not read a frame from the stream {self.url}.")
            print("This might happen if the stream is empty or disconnected immediately.")
            return None
import asyncio
import websockets
import json
import platform
import socket
import base64
import logging

from config import WS_SERVER_IP, WS_SERVER_PORT, RTSP_URL
from warn import WarnSession
from kill import kill
from rtsp import RTSP

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    level=logging.DEBUG,
    datefmt='%m/%d/%Y %I:%M:%S %p',
)
log = logging.getLogger('main')
warn = WarnSession()
rtsp = RTSP(RTSP_URL)


async def send_heartbeat(websocket):
    """Send a heartbeat message to the server."""
    while True:
        # Get IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        ip = s.getsockname()[0]
        s.close()

        # Send a simple heartbeat message
        await websocket.send(json.dumps({"type": "heartbeat", "hostname": platform.node(), "ip": ip}))
        await asyncio.sleep(1)  # Send heartbeat every 1 seconds


async def receive_messages(websocket):
    """Receive and process messages from the server."""
    async for message in websocket:
        log.debug(f"Received message from server: {message}")
        try:
            data = json.loads(message)
            if data.get("type") == "broadcast":
                ws_msg = data.get('message')
                log.info(f"Broadcast Message: {ws_msg}")

                if ws_msg == 'kill':
                    kill_type = data.get('killType', 'default')
                    kill(kill_type)

                elif ws_msg == 'movement':
                    image = rtsp.get_frame_bytes()
                    warn.start(image)

                else:
                    log.error(f"Unknown ICE message: {ws_msg}")

        except json.JSONDecodeError:
            log.error(f"Received non-JSON message: {message}")
        except Exception as e:
            log.error(f"Error processing received message: {e}")


def base64_to_img(base64_string):
    try:
        decoded_bytes = base64.b64decode(base64_string)
        return decoded_bytes
    except Exception as e:
        log.critical(f"Error decoding Base64 string: {e}")
        return None


async def connect_to_ha():
    """Connect to Home Assistant WebSocket server."""
    uri = f"ws://{WS_SERVER_IP}:{WS_SERVER_PORT}"
    while True:
        try:
            log.info(f"Connecting to {uri}...")
            async with websockets.connect(uri) as websocket:
                log.info(f"Connected to {uri}")

                # Start sending heartbeats and receiving messages concurrently
                await asyncio.gather(
                    send_heartbeat(websocket),
                    receive_messages(websocket)
                )

        except websockets.exceptions.ConnectionClosed:
            log.error(f"Connection closed. Retrying in 5 seconds...")
        except ConnectionRefusedError:
            log.error(f"Connection refused. Ensure Home Assistant is running and accessible at {uri}. Retrying in 5 seconds...")
        except websockets.exceptions.WebSocketException as e:
            log.error(f"WebSocket error: {e}. Retrying in 5 seconds...")
        except Exception as e:
            log.error(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")
        await asyncio.sleep(5) # Wait before retrying connection

if __name__ == "__main__":
    rtsp.connect()
    asyncio.run(connect_to_ha())
import logging

import socketio

ENDPOINT = 'http://127.0.0.1:8080'
CLIENT_NAME = 'Yongj-PC01'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)
sio = socketio.Client()

@sio.event
def connect():
    log.info('Connected to server')

@sio.event
def message(data):
    log.info('Received from server: ' + data)

@sio.event
def connect_error(data):
    log.error("The connection failed!")

@sio.event
def disconnect():
    log.info('Disconnected from server')

if __name__ == '__main__':
    try:
        log.info(f"Attempting to connect to {ENDPOINT}")
        sio.connect(
            url=ENDPOINT,
            headers={
                'X-Client-Type': 'pc',
                'X-Client-Name': CLIENT_NAME
            }
        )
        log.info("Client connected. Waiting for events...")
        sio.wait()
    except socketio.exceptions.ConnectionError as e:
        log.error(f"Could not connect to the server: {e}")
    except KeyboardInterrupt:
        log.info("Client stopped by user.")
    finally:
        log.info("Client disconnecting.")
        sio.disconnect()
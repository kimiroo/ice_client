import logging

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
)

import sys
import ctypes
import datetime
import asyncio
import uuid

import socketio
import aiohttp

from utils.config import config
from utils.states import states
from objects.event import Event
from warn.warn import WarnSession
from kill.kill import Killer

log = logging.getLogger('main')

sio = socketio.AsyncClient()
warn = WarnSession()
kill = Killer(warn)

def is_admin_windows():
    """Checks if the script is running with administrator privileges on Windows."""
    try:
        # Check if the process token has administrator privileges
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        return False

async def handle_event(event, is_internal):
    if not is_internal:
        states.last_event_id = event['id']
        await sio.emit('ack', {'id': event['id']})

    event_obj = Event(is_internal=is_internal,
                      id=event['id'],
                      event=event['event'],
                      type=event['type'],
                      source=event['source'],
                      timestamp=event['timestamp'],
                      data=event.get('data', {}))

    can_show = False

    async def get_camera_frame():
        image_bytes = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(config.camera_frame_url) as response:
                    response.raise_for_status()
                    image_bytes = await response.read()
        except aiohttp.ClientError as e:
            log.error(f'Error getting camera frame: {e}')
        except Exception as e:
            log.error(f'An unexpected error occurred: {e}')
        return image_bytes

    if event_obj.type == 'client' and event_obj.source == 'server':
        await states.push_event(event_obj)
        log.info(f'[CLIENT] Client \'{event_obj.data['client']['name']}\' {event_obj.event}')

    elif event_obj.event == 'zero_client' and event_obj.source == 'self' and not await states.is_previous_event_valid(event_obj.type, event_obj.event):
        await states.push_event(event_obj)
        log.warning(f'[CLIENT] Zero client detected: PC: {len(states.client_list_pc)}, HA: {len(states.client_list_ha)}, HTML: {len(states.client_list_html)}')
        warn.start(f'{event_obj.source}_{event_obj.type}_{event_obj.event}', 'ZERO CLIENT', f'PC: {len(states.client_list_pc)}, HA: {len(states.client_list_ha)}, HTML: {len(states.client_list_html)}', no_audio=True)

    elif event_obj.type == 'connection' and not await states.is_previous_event_valid(event_obj.type, event_obj.event):
        await states.push_event(event_obj)
        log.warning(f'[CONNECTION] Server {event_obj.event}.')
        warn.start(f'{event_obj.source}_{event_obj.type}_{event_obj.event}', event_obj.event.upper(), 'SERVER DISCONNECTED', no_audio=True)

    elif event_obj.type == 'onvif' and not await states.is_previous_event_valid(event_obj.type):
        await states.push_event(event_obj)
        log.warning(f'[ONVIF] {event_obj.event.upper()} detected.')
        warn.start(f'{event_obj.source}_{event_obj.type}_{event_obj.event}', 'MOTION DETECTED', 'Loading...', is_priority=True)
        image_bytes = await get_camera_frame()
        warn.update_image(image_bytes)

    elif event_obj.type == 'user':
        await states.push_event(event_obj)

        if event_obj.event == 'kill':
            log.warning(f'[USER] {event_obj.event.upper()} Initiated. (Kill mode: {event_obj.data.get("killMode", "unknown")})')
            kill_mode = event_obj.data.get('killMode', 'unknown')
            warn.start(f'{event_obj.source}_{event_obj.type}_{event_obj.event}', 'KILLING', f'KILLING...\n(mode: {kill_mode})', no_audio=True, is_priority=True)
            await kill.kill(kill_mode)
        elif event_obj.event == 'ignore':
            log.info(f'[USER] {event_obj.event.upper()} Initiated.')
            warn.stop('_force_stop_all')

@sio.event
async def connect():
    log.info('Connected to server. Introducing self...')
    states.last_heartbeat = datetime.datetime.now()
    payload = {
        'name': config.client_name,
        'type': 'pc'
    }
    if states.last_event_id:
        payload['lastEventID'] = states.last_event_id
    await sio.emit('introduce', payload)

@sio.event
async def disconnect():
    log.warning('Disconnected from server.')
    states.is_connected = False
    event_payload = {
        'id': str(uuid.uuid4()),
        'event': 'disconnected',
        'type': 'connection',
        'source': 'self',
        'timestamp': datetime.datetime.now().isoformat()
    }
    await handle_event(event_payload, is_internal=True)

@sio.on('event')
async def on_event(data = {}):
    await handle_event(data['event'], is_internal=False)

@sio.on('event_ignored')
async def on_event_ignored(data = {}):
    log.debug(f'Event ignored: {data}')

@sio.on('ping')
async def on_ping(data = {}):
    states.is_connected = True
    states.last_heartbeat = datetime.datetime.now()
    await sio.emit('get')

@sio.on('get_result')
async def on_get_result(data = {}):
    event_list = data.get('eventList', {})
    client_list = data.get('clientList', {})

    states.is_armed = data.get('isArmed', False)

    new_client_list_pc = []
    new_client_list_ha = []
    new_client_list_html = []

    for client in client_list:
        if client['type'] == 'pc':
            new_client_list_pc.append(client)
        elif client['type'] == 'ha':
            new_client_list_ha.append(client)
        elif client['type'] == 'html':
            new_client_list_html.append(client)

    states.client_list_pc = new_client_list_pc
    states.client_list_ha = new_client_list_ha
    states.client_list_html = new_client_list_html

    new_event_list = []
    acked_event_list = []
    for event in event_list:
        if not await states.is_event_duplicate(event['id']):
            new_event_list.append(event)
        else:
            acked_event_list.append(event)

    if new_event_list:
        log.warning(f'Detected a delay in processing event: {len(event_list)} events in queue')
        tasks = [handle_event(event, is_internal=False) for event in new_event_list]
        await asyncio.gather(*tasks)

    for event in acked_event_list: # ACK again just to make sure
        await sio.emit('ack', {'id': event['id']})

    await sio.emit('pong')

    if (states.is_armed and
        (len(states.client_list_pc) == 0 or
         len(states.client_list_ha) == 0 or
         len(states.client_list_html) == 0)):
        event_payload = {
            'id': str(uuid.uuid4()),
            'event': 'zero_client',
            'type': 'client',
            'source': 'self',
            'timestamp': datetime.datetime.now().isoformat()
        }
        await handle_event(event_payload, is_internal=True)
    elif (states.is_armed and states.current_event == 'self_client_zero_client'):
        warn.stop('self_client_zero_client')

async def connection_monitoring_worker():
    await asyncio.sleep(1) # Grace startup (prevent rush alert)
    while True:
        try:
            time_now = datetime.datetime.now()
            time_diff = time_now - states.last_heartbeat
            if not states.is_connected or time_diff.total_seconds() > 1:
                states.is_connected = False
                event_payload = {
                    'id': str(uuid.uuid4()),
                    'event': 'disconnected',
                    'type': 'connection',
                    'source': 'self',
                    'timestamp': datetime.datetime.now().isoformat()
                }
                await handle_event(event_payload, is_internal=True)
            elif states.current_event == 'self_connection_disconnected':
                warn.stop('self_connection_disconnected')
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            log.info('Stopping connection monitoring worker...')
            break

async def main():
    log.info('Starting background workers...')
    task_event_cleaner = asyncio.create_task(states.clear_old_events_worker())
    task_connection_monitoring = asyncio.create_task(connection_monitoring_worker())
    task_obs = asyncio.create_task(kill.obs_connection_worker())
    while True:
        log.info('Starting main loop...')
        do_break = False
        try:
            await sio.connect(config.ice_server_url)
            await sio.wait()
        except KeyboardInterrupt:
            log.info('Client stopped by user.')
            do_break = True
        except Exception as e:
            log.error(f'Error in main loop: {e}')
        finally:
            await sio.disconnect()
            await asyncio.sleep(0.1)
            if do_break:
                break

if __name__ == '__main__':
    if not is_admin_windows():
        log.critical(f'Client app is not running as administrator. Relaunch app with administrator privileges.')
        log.info('Exiting...')
        sys.exit(1)
    asyncio.run(main())
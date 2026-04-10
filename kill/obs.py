import asyncio
import logging
import subprocess
from multiprocessing import Queue

import obsws_python as obs
import psutil

from utils.config import config

log = logging.getLogger(__name__)

class OBSWrapper:
    def __init__(self):
        self.obs = None
        self.connected = False

    def connect(self):
        try:
            self.obs = obs.ReqClient(
                host=config.obs_host,
                port=config.obs_port,
                password=config.obs_password,
                timeout=3
            )
            self.connected = True
            log.info('Successfully connected to OBS.')
        except Exception as e:
            self.obs = None
            log.error(f'Failed to connect to OBS: {e}')

    def ping(self):
        try:
            self.obs.get_version()
            log.debug('OBS connection is active. Waiting...')
        except Exception as e:
            self.obs = None
            self.connected = False
            log.warning(f'OBS connection failed: {e}. Attempting to reconnect...')

    def stop_recording(self):
        if self.obs is not None:
            if self.obs.get_record_status():
                log.info('Stopping OBS recording...')
                self.obs.stop_record()
                log.info('Successfully stopped OBS recording.')
            else:
                log.info('OBS not recording. Skipping...')
        else:
            log.info('OBS not running. Skipping...')

    def disconnect(self):
        self.obs.disconnect()

def is_running(process_name):
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

async def obs_connection_worker(obs: OBSWrapper):
    while True:
        try:
            if not obs.connected and config.obs_enabled:
                if is_running('obs64.exe') or is_running('obs.exe'):
                    log.info('OBS running but not connected. Trying to connect...')
                    obs.connect()
        except asyncio.CancelledError:
            obs.disconnect()
            break
        except Exception as e:
            log.error(f'Exception occured while monitoring OBS connection: {e}')

        await asyncio.sleep(1)

async def obs_kill_worker(obs: OBSWrapper, queue: Queue):
    loop = asyncio.get_running_loop()

    while True:
        try:
            payload = await loop.run_in_executor(None, queue.get)

            if payload.get('kill'):
                obs.stop_recording()
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f'Unknown error: {e}')
            await asyncio.sleep(.1)

def start_obs_worker(queue: Queue):
    asyncio.run(start_obs_worker_async(queue))

async def start_obs_worker_async(queue: Queue):
    obs = OBSWrapper()

    await asyncio.gather(
        obs_connection_worker(obs),
        obs_kill_worker(obs, queue)
    )
import logging
import asyncio
import subprocess
from typing import Tuple, TYPE_CHECKING

import obsws_python as obs

from utils.config import config

if TYPE_CHECKING:
    from warn.warn import WarnSession

log = logging.getLogger(__name__)


class Killer:
    def __init__(self, warn_session_instance: 'WarnSession'):
        self.obs = None
        self.warn = warn_session_instance

    def kill(self, kill_mode: str):
        kill_config = config.kill_config.get(kill_mode, None)

        if kill_config is None:
            log.critical(f'Unknown kill mode: {kill_mode}')
            self.warn.start('self_kill_unknown', 'INVALID KILL MODE', f'UNDEFINED KILL MODE:\n{kill_mode}', is_priority=True)
            return

        taskkill_list = kill_config.get('taskkill', [])
        commands_list = kill_config.get('commands', [])
        obs_mode = kill_config.get('obs', None)

        self._kill_processes(taskkill_list)
        self._run_commands(commands_list)

        if obs_mode == 'stop' and config.obs_enabled:
            try:
                if self.obs is not None:
                    self.obs.stop_record()
                    log.info('Successfully stopped OBS recording.')
                else:
                    log.error(f'Failed to stop OBS recording: OBS Not connected')
            except Exception as e:
                log.error(f'Failed to stop OBS recording: {e}')


    def _kill_processes(self, process_list: list) -> Tuple[bool, str]:
        for process in process_list:
            try:
                subprocess.run(['taskkill', '/f', '/im', process], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                log.info(f'Successfully terminated \'{process}\'.')
            except subprocess.CalledProcessError as e:
                log.info(f'Failed to terminate \'{process}\': {e}')
            except Exception as e:
                log.error(f'Unknown error occurred while terminating process \'{process}\': {e}')

    def _run_commands(self, commands_list: list) -> Tuple[bool, str]:
        for commands in commands_list:
            try:
                if type(commands) == list:
                    subprocess.run(commands, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    log.info(f'Successfully executed command: \'{commands}\'.')
                else:
                    log.error(f'Command has to be in list format. \'{commands}\' is {type(commands)}.')
            except subprocess.CalledProcessError as e:
                log.error(f'Failed to execute command: \'{commands}\'')
            except Exception as e:
                log.error(f'Unknown error occurred while executing command \'{commands}\': {e}')

    async def obs_connection_worker(self):
        if not config.obs_enabled:
            log.info('OBS connection worker is disabled.')
            return

        log.info('Starting OBS connection worker...')
        try:
            self.obs = obs.ReqClient(
                host=config.obs_host,
                port=config.obs_port,
                password=config.obs_password,
                timeout=3
            )
            log.info('Successfully connected to OBS.')
        except Exception as e:
            log.error(f'Failed to connect to OBS: {e}')
        while True:
            try:
                # Check for existing connection.
                # If connected, this call will succeed.
                # If not, it will raise an exception.
                self.obs.get_version()
                log.debug('OBS connection is active. Waiting...')
            except asyncio.CancelledError:
                log.info('Stopping OBS connection worker...')
                break  # Exit the loop on cancellation
            except Exception as e:
                # Catch any other exception to handle connection issues.
                log.debug(f'OBS connection failed: {e}. Attempting to reconnect...')
                self.obs = None # Ensure old client is not used

                try:
                    # Attempt to create a new connection
                    self.obs = obs.ReqClient(
                        host=config.obs_host,
                        port=config.obs_port,
                        password=config.obs_password,
                        timeout=1
                    )
                    log.info('Successfully reconnected to OBS.')
                except asyncio.CancelledError:
                    log.info('Stopping OBS connection worker...')
                    break
                except Exception as e:
                    log.error(f'Failed to connect to OBS: {e}. Retrying in 1 second...')
                    self.obs = None

            await asyncio.sleep(1)
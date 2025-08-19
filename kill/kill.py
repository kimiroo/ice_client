import logging
import asyncio
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

    async def kill(self, kill_mode: str):
        kill_config = config.kill_config.get(kill_mode, None)

        if kill_config is None:
            log.critical(f'Unknown kill mode: {kill_mode}')
            self.warn.start('self_kill_unknown', 'INVALID KILL MODE', f'UNDEFINED KILL MODE:\n{kill_mode}', is_priority=True)
            return

        taskkill_list = kill_config.get('taskkill', [])
        commands_list = kill_config.get('commands', [])
        obs_mode = kill_config.get('obs', None)

        await self.terminate_processes(taskkill_list)
        await self._run_commands(commands_list)

        if obs_mode == 'stop' and config.obs_enabled:
            await self.stop_obs_recording()

    async def _terminate_process(self, process: str) -> Tuple[bool, str]:
        try:
            process_obj = await asyncio.create_subprocess_exec(
                'taskkill',
                '/f',
                '/im',
                process,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process_obj.communicate()

            if process_obj.returncode == 0:
                log.info(f'Successfully terminated \'{process}\'.')
            else:
                error_message = stderr.decode(errors='ignore').strip()
                log.info(f'Failed to terminate \'{process}\': {error_message}')

        except Exception as e:
            log.error(f'Unknown error occurred while terminating process \'{process}\': {e}')

    async def terminate_processes(self, process_list: list):
        # Create a list of tasks for each process to be terminated.
        tasks = [self._terminate_process(process) for process in process_list]

        # Run all tasks concurrently.
        await asyncio.gather(*tasks)

    async def _execute_command(self, command: list) -> None:
        if not isinstance(command, list):
            log.error(f'Command must be in list format. \'{command}\' is {type(command)}.')
            return

        try:
            # Create a non-blocking subprocess.
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            log.info(f'Started background command: \'{command}\'. Process ID: {process.pid}')

        except FileNotFoundError:
            log.error(f"Command not found: '{command[0]}'. Check your system's PATH.")
        except Exception as e:
            log.error(f'Unknown error occurred while executing command \'{command}\': {e}')

    async def _run_commands(self, commands_list: list) -> None:
        # Create a list of tasks for each command.
        tasks = [self._execute_command(command) for command in commands_list]

        # Run all tasks concurrently and wait for them to complete.
        await asyncio.gather(*tasks)

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

    async def stop_obs_recording(self):
        try:
            if self.obs is not None:
                if self.obs.get_record_status():
                    self.obs.stop_record()
                    log.info('Successfully stopped OBS recording.')
                else:
                    log.info('Failed to stop OBS recording: OBS Not recording')
            else:
                log.error(f'Failed to stop OBS recording: OBS Not connected')
        except Exception as e:
            log.error(f'Failed to stop OBS recording: {e}')
import logging
import asyncio
from multiprocessing import Process, Queue
from typing import Tuple, TYPE_CHECKING

from utils.config import config
from kill.obs import start_obs_worker

if TYPE_CHECKING:
    from warn.warn import WarnSession

log = logging.getLogger(__name__)


class Killer:
    def __init__(self, warn_session_instance: 'WarnSession'):
        self.obs = None
        self.warn = warn_session_instance
        self.obs_queue = Queue()

        self.obs_worker = None

    def start_worker(self):
        self.obs_worker = Process(target=start_obs_worker, args=(self.obs_queue, ))
        self.obs_worker.daemon = False
        self.obs_worker.start()

    async def kill(self, kill_mode: str):
        kill_config = config.kill_config.get(kill_mode, None)

        if kill_config is None:
            log.critical(f'Unknown kill mode: {kill_mode}')
            self.warn.start('self_kill_unknown', 'INVALID KILL MODE', f'UNDEFINED KILL MODE:\n{kill_mode}', is_priority=True)
            return

        taskkill_list = kill_config.get('taskkill', [])
        commands_list = kill_config.get('commands', [])

        await self.terminate_processes(taskkill_list)
        await self._run_commands(commands_list)

        # Send OBS worker stop signal
        self.obs_queue.put_nowait({'kill': True})

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

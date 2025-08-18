import logging
import asyncio
import datetime
from typing import TYPE_CHECKING, List, Union

from utils.config import config

if TYPE_CHECKING:
    from objects.event import Event

log = logging.getLogger(__name__)


class States:
    def __init__(self):
        self._lock = asyncio.Lock()

        self.is_connected: bool = False
        self.last_heartbeat: datetime.datetime = datetime.datetime(1900,1,1,0,0,0,0)
        self.is_armed: bool = False
        self.last_event_id: Union[str, None] = None

        self.client_list_pc: list = []
        self.client_list_ha: list = []
        self.client_list_html: list = []

        self.event_list: List['Event'] = []
        self.current_event: str = ''

    async def push_event(self, event: 'Event'):
        async with self._lock:
            self.event_list.append(event)

    async def is_previous_event_valid(self, event_type: str, event_name: str = None):
        async with self._lock:
            time_now = datetime.datetime.now()

            for event in self.event_list:
                time_diff = time_now - event.timestamp

                if time_diff.total_seconds() < config.warn_duration and event.type == event_type:
                    if event_name is None or event.event == event_name:
                        return True

            return False

    async def clear_old_events(self):
        async with self._lock:
            time_now = datetime.datetime.now()

            def is_valid_event(event: 'Event'):
                time_diff = time_now - event.timestamp
                return time_diff.total_seconds() < config.warn_duration

            self.event_list = list(filter(is_valid_event, self.event_list))

    async def clear_old_events_worker(self):
        log.info('Starting old events cleaner worker...')
        while True:
            try:
                await self.clear_old_events()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                log.info('Stopping old events cleaner worker...')
                break


states = States()
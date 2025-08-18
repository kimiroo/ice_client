from typing import Union
import datetime

class Event:
    def __init__(self,
                 is_internal: bool,
                 id: str,
                 event: str,
                 type: str,
                 source: str,
                 timestamp: Union[str, datetime.datetime],
                 data: dict = None):

        self.is_internal: bool = is_internal
        self.id: str = id
        self.event: str = event
        self.type: str = type
        self.source: str = source
        self.timestamp: datetime.datetime = timestamp if isinstance(timestamp, datetime.datetime) else datetime.datetime.fromisoformat(timestamp)
        self.data: Union[dict, None] = data if data is not None else {}
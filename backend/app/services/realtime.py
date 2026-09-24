"""In-memory queues used to deliver live transcript events.

SQLite remains the source of truth. These queues only notify connected pages
about newly saved text and disappear when the API process restarts.
"""

import asyncio


class EventHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault(session_id, set()).add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue) -> None:
        subscribers = self._subscribers.get(session_id)
        if subscribers is None:
            return

        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(session_id, None)

    async def publish(self, session_id: str, message: dict) -> None:
        # Iterate over a copy so an unsubscribe during delivery is harmless.
        for queue in list(self._subscribers.get(session_id, set())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                # Protect the API if a very slow page stops reading its queue.
                pass

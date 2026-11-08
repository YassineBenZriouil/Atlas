"""In-process event fan-out for the core service's SSE stream."""

from __future__ import annotations

import queue
import threading
import time
from collections import deque
from typing import Any

Event = dict[str, Any]


class EventBus:
    """Keeps a short history (so a window opened later can show what
    already happened) and pushes every new event to each subscriber's
    queue. A `None` on a queue means the bus closed."""

    def __init__(self, history_size: int = 200) -> None:
        self._lock = threading.Lock()
        self._history: deque[Event] = deque(maxlen=history_size)
        self._subscribers: list[queue.Queue[Event | None]] = []
        self._next_id = 1

    def publish(self, kind: str, message: str = "", **data: Any) -> Event:
        with self._lock:
            event = {"id": self._next_id, "time": time.time(), "kind": kind, "message": message}
            event.update(data)
            self._next_id += 1
            self._history.append(event)
            for subscriber in self._subscribers:
                subscriber.put(event)
        return event

    def history(self) -> list[Event]:
        with self._lock:
            return list(self._history)

    def subscribe(self) -> queue.Queue[Event | None]:
        subscriber: queue.Queue[Event | None] = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[Event | None]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def close(self) -> None:
        with self._lock:
            for subscriber in self._subscribers:
                subscriber.put(None)
            self._subscribers.clear()

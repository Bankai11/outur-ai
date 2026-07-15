"""Lightweight, asynchronous event bus abstraction for Outur AI."""

from __future__ import annotations
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger(__name__)

# Subscriber type: takes event type and event data dict, returns None asynchronously
Subscriber = Callable[[str, Dict[str, Any]], Awaitable[None]]

class EventBus:
    """Singleton Event Bus coordinating pub/sub communication."""
    
    _instance: EventBus | None = None
    _subscribers: Dict[str, List[Subscriber]]
    
    def __new__(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance
        
    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        """Register a callback for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.info(f"Registered subscriber {callback.__name__} to event: {event_type}")

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to all registered subscribers concurrently."""
        logger.info(f"Publishing event: {event_type}")
        subscribers = self._subscribers.get(event_type, [])
        if not subscribers:
            logger.debug(f"No subscribers registered for event: {event_type}")
            return
            
        tasks = [
            self._run_subscriber(sub, event_type, data)
            for sub in subscribers
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_subscriber(self, sub: Subscriber, event_type: str, data: Dict[str, Any]) -> None:
        try:
            await sub(event_type, data)
        except Exception as e:
            logger.error(
                f"Error executing subscriber {sub.__name__} for event {event_type}: {e}",
                exc_info=True
            )

# Global event bus instance
event_bus = EventBus()

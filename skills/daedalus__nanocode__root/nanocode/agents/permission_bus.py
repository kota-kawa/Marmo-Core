"""Event bus for permission system - matches OpenCode's event-driven architecture."""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

logger = logging.getLogger("nanocode.permission_bus")


class PermissionEventType(Enum):
    """Permission event types."""

    ASKED = "permission.asked"
    ANSWERED = "permission.answered"
    REPLIED = "permission.replied"


@dataclass
class PermissionAskedEvent:
    """Event fired when a permission is requested."""

    id: str
    session_id: str
    tool_name: str
    permission: str
    metadata: dict


@dataclass
class PermissionRepliedEvent:
    """Event fired when a permission is responded to."""

    id: str
    session_id: str
    reply: str  # "allow", "deny", "reject"


PermissionEvent = PermissionAskedEvent | PermissionRepliedEvent


class PermissionBus:
    """
    Event bus for permission events - similar to OpenCode's Bus system.
    
    This allows the agent to emit permission events and continue processing
    without blocking, while the UI can subscribe to these events and
    show permission dialogs.
    """

    _instance = None

    def __new__(cls) -> "PermissionBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._handlers: dict[PermissionEventType, list[Callable]] = {
            PermissionEventType.ASKED: [],
            PermissionEventType.ANSWERED: [],
            PermissionEventType.REPLIED: [],
        }
        self._pending_queue: asyncio.Queue[PermissionAskedEvent] = asyncio.Queue()
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._initialized = True

    def subscribe(self, event_type: PermissionEventType, handler: Callable) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")

    def unsubscribe(self, event_type: PermissionEventType, handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Handler unsubscribed from {event_type.value}")

    async def emit(self, event: PermissionEvent) -> None:
        """Emit an event to all subscribers."""
        event_type = (
            PermissionEventType.ASKED
            if isinstance(event, PermissionAskedEvent)
            else PermissionEventType.REPLIED
        )

        logger.debug(f"Emitting event: {event_type.value} - {event}")

        for handler in self._handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    async def request_permission(
        self,
        session_id: str,
        tool_name: str,
        permission: str,
        metadata: dict,
    ) -> str:
        """
        Request permission with async waiting.
        
        Emits a permission.asked event and waits for the corresponding
        permission.replied event. Returns the reply ('allow', 'deny', 'reject').
        
        This matches OpenCode's pattern where permissions are queued and
        processed sequentially without blocking the main agent loop.
        """
        request_id = f"perm_{len(self._pending_requests)}_{id(metadata)}"

        event = PermissionAskedEvent(
            id=request_id,
            session_id=session_id,
            tool_name=tool_name,
            permission=permission,
            metadata=metadata,
        )

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        await self.emit(event)

        try:
            reply = await asyncio.wait_for(future, timeout=5)
            return reply
        except TimeoutError:
            logger.warning(f"Permission request {request_id} timed out")
            self._pending_requests.pop(request_id, None)
            return "reject"
        except asyncio.CancelledError:
            logger.debug(f"Permission request {request_id} cancelled")
            self._pending_requests.pop(request_id, None)
            raise

    def reply_permission(self, request_id: str, reply: str) -> None:
        """
        Reply to a pending permission request.
        
        This is called by the UI when user responds to a permission dialog.
        """
        if request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.done():
                future.set_result(reply)
                logger.debug(f"Permission {request_id} replied with: {reply}")

            event = PermissionRepliedEvent(
                id=request_id,
                session_id="",  # Will be filled by emitter
                reply=reply,
            )
            asyncio.create_task(self.emit(event))
        else:
            logger.warning(f"No pending permission request: {request_id}")

    def has_pending(self) -> bool:
        """Check if there are pending permission requests."""
        return len(self._pending_requests) > 0

    def get_pending_count(self) -> int:
        """Get count of pending permission requests."""
        return len(self._pending_requests)


def get_permission_bus() -> PermissionBus:
    """Get the singleton permission bus instance."""
    return PermissionBus()
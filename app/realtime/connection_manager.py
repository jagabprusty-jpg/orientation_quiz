import asyncio
import json
import logging
from typing import Dict, Set, Union, Any, List
from fastapi import WebSocket
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages real-time WebSocket connections for live quiz participants.
    
    Features:
    - Supports multiple concurrent connections per student (multi-tab / reconnections).
    - Thread-safe and async-safe connection registration and deregistration.
    - Resilient broadcasting: a failed or severed client connection is gracefully cleaned up
      without disrupting delivery to other connected students.
    - Single-process in-memory design with clear interfaces for future Redis Pub/Sub integration.
    """

    def __init__(self):
        # Map: student_id -> Set of active WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, student_id: int, websocket: WebSocket) -> None:
        """Accept and register a new student WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            if student_id not in self._connections:
                self._connections[student_id] = set()
            self._connections[student_id].add(websocket)
        logger.info(
            f"Student {student_id} connected. Active connections for student: {len(self._connections[student_id])}. Total active students: {len(self._connections)}"
        )

    async def disconnect(self, student_id: int, websocket: WebSocket) -> None:
        """Deregister a disconnected WebSocket for a student."""
        async with self._lock:
            if student_id in self._connections:
                self._connections[student_id].discard(websocket)
                if not self._connections[student_id]:
                    del self._connections[student_id]
        logger.info(f"Student {student_id} socket disconnected.")

    def _serialize_event(self, event: Union[BaseModel, Dict[str, Any]]) -> str:
        """Helper to serialize an event payload to a JSON string."""
        if isinstance(event, BaseModel):
            return event.model_dump_json()
        return json.dumps(event, default=str)

    async def send_to_student(self, student_id: int, event: Union[BaseModel, Dict[str, Any]]) -> None:
        """Send an event directly to all active connections for a single student."""
        json_str = self._serialize_event(event)
        async with self._lock:
            sockets = list(self._connections.get(student_id, set()))

        dead_sockets: List[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_text(json_str)
            except Exception as e:
                logger.warning(f"Error sending message to student {student_id}: {e}")
                dead_sockets.append(socket)

        if dead_sockets:
            async with self._lock:
                for dead in dead_sockets:
                    if student_id in self._connections:
                        self._connections[student_id].discard(dead)
                        if not self._connections[student_id]:
                            del self._connections[student_id]

    async def broadcast(self, event: Union[BaseModel, Dict[str, Any]]) -> None:
        """
        Broadcast an event to all connected students across all active sockets.
        Failed sockets are identified and pruned without stopping the broadcast.
        """
        json_str = self._serialize_event(event)
        
        # Take a snapshot of all sockets under lock
        async with self._lock:
            all_entries = [(s_id, sock) for s_id, sockets in self._connections.items() for sock in sockets]

        if not all_entries:
            return

        dead_entries: List[tuple[int, WebSocket]] = []

        # Deliver to each socket
        for student_id, socket in all_entries:
            try:
                await socket.send_text(json_str)
            except Exception as e:
                logger.warning(f"Broadcast error on student {student_id} socket: {e}")
                dead_entries.append((student_id, socket))

        # Cleanup any dead sockets identified during broadcast
        if dead_entries:
            async with self._lock:
                for student_id, socket in dead_entries:
                    if student_id in self._connections:
                        self._connections[student_id].discard(socket)
                        if not self._connections[student_id]:
                            del self._connections[student_id]

    @property
    def active_students_count(self) -> int:
        """Number of unique active students currently connected."""
        return len(self._connections)

    @property
    def total_connections_count(self) -> int:
        """Total number of open WebSocket connections across all students."""
        return sum(len(socks) for socks in self._connections.values())


# Global singleton connection manager
connection_manager = ConnectionManager()

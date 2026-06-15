import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
import structlog
from backend.config import settings

logger = structlog.get_logger()

class WebSocketManager:
    def __init__(self) -> None:
        # Store active connections in this process (session_id -> set of websockets)
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        
        logger.info("WebSocket connected", session_id=session_id)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        logger.info("WebSocket disconnected", session_id=session_id)

    async def broadcast(self, session_id: str, message: dict) -> None:
        websockets = self.active_connections.get(session_id, set()).copy()
        for ws in websockets:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warn("Failed to send message over websocket", error=str(e))
                await self.disconnect(session_id, ws)

ws_manager = WebSocketManager()

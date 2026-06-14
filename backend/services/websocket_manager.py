import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket
import redis.asyncio as aioredis
import structlog
from backend.config import settings

logger = structlog.get_logger()

class WebSocketManager:
    def __init__(self) -> None:
        self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        # Store active connections in this process (session_id -> set of websockets)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Pubsub listener tasks: session_id -> Task
        self.pubsub_tasks: Dict[str, asyncio.Task[None]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        
        # Track connections in Redis
        conn_key = f"ws:session:{session_id}:connections"
        await self.redis_client.sadd(conn_key, str(id(websocket)))
        await self.redis_client.expire(conn_key, 3600)  # 1 hour TTL
        
        # Start listening to Redis channel for this session if not already listening
        if session_id not in self.pubsub_tasks:
            self.pubsub_tasks[session_id] = asyncio.create_task(self._listen_to_channel(session_id))
            
        logger.info("WebSocket connected", session_id=session_id)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                # Clean up Redis pubsub task
                if session_id in self.pubsub_tasks:
                    self.pubsub_tasks[session_id].cancel()
                    del self.pubsub_tasks[session_id]
        
        conn_key = f"ws:session:{session_id}:connections"
        await self.redis_client.srem(conn_key, str(id(websocket)))
        logger.info("WebSocket disconnected", session_id=session_id)

    async def broadcast(self, session_id: str, message: dict) -> None:
        # Publish to Redis channel so all instances of the backend can pick it up
        channel = f"channel:session:{session_id}"
        await self.redis_client.publish(channel, json.dumps(message))
        logger.debug("Broadcasted message to channel", session_id=session_id, message=message)

    async def _listen_to_channel(self, session_id: str) -> None:
        channel_name = f"channel:session:{session_id}"
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel_name)
        
        try:
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    # Send to all websockets in this process
                    websockets = self.active_connections.get(session_id, set()).copy()
                    for ws in websockets:
                        try:
                            await ws.send_json(data)
                        except Exception as e:
                            logger.warn("Failed to send message over websocket, cleaning up", error=str(e))
                            await self.disconnect(session_id, ws)
        except asyncio.CancelledError:
            logger.info("Pubsub listener cancelled for session", session_id=session_id)
        except Exception as e:
            logger.error("Error in pubsub listener", error=str(e), session_id=session_id)
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

ws_manager = WebSocketManager()

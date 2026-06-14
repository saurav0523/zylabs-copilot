from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from backend.services.websocket_manager import ws_manager

logger = structlog.get_logger()
router = APIRouter()

@router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint to stream real-time workflow progress to the browser."""
    logger.info("New WebSocket request", session_id=session_id)
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            # Listen to messages from the client. Useful for detecting client disconnects.
            data = await websocket.receive_text()
            logger.debug("Received message from client", session_id=session_id, data=data)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket connection encountered an error", error=str(e), session_id=session_id)
    finally:
        await ws_manager.disconnect(session_id, websocket)

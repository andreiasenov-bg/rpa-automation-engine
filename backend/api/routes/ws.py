"""WebSocket endpoint for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging
import json

from core.security import verify_token
from api.websockets.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time execution and notification updates.

    Authenticate via ?token=<jwt_access_token> query parameter.
    NOTE: JWT is passed as query parameter (not header) because browsers cannot
    send custom headers during WebSocket upgrade. This is acceptable for JWTs as
    they are:
    1. Cryptographically signed (tamper-proof)
    2. Time-limited
    3. Requires valid authorization to obtain

    Server pushes events:
    - execution.status_changed: {execution_id, status, workflow_id}
    - execution.log: {execution_id, level, message, timestamp}
    - notification: {title, message, priority, metadata}
    - trigger.fired: {trigger_id, workflow_id, execution_id}
    """
    # Authenticate
    try:
        payload = verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    org_id = payload.org_id
    user_id = payload.sub

    # Connect
    await manager.connect(websocket, org_id=org_id, user_id=user_id)

    try:
        while True:
            # Receive and handle client messages (keepalive pings)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await manager.disconnect(websocket, org_id=org_id, user_id=user_id)

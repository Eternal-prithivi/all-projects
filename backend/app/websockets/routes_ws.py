from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.auth.auth_utils import get_current_user_ws
from app.users.user_model import UserInDB
from .connection_manager import manager

# The redundant prefix has been removed
router = APIRouter(tags=["WebSockets"])

@router.websocket("/status")
async def websocket_endpoint(
    websocket: WebSocket,
    user: UserInDB = Depends(get_current_user_ws)
):
    """
    Establishes a WebSocket connection for a user after authenticating them
    via a token in the query parameters.
    """
    user_id = user.username
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)

@router.post("/notify/{user_id}")
async def notify_user(user_id: str):
    """

    An internal endpoint for the Celery worker to call.
    It sends a message to a specific user over the WebSocket.
    """
    await manager.send_personal_message("job_complete", user_id)
    return {"status": "notification sent"}

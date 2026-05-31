"""WebSocket endpoints — job progress, project events, log streaming.

Job progress streams via Redis pub/sub: channel job:{job_id}.
Progress updates published every 500ms during active generation.
WebSocket auto-reconnects with exponential backoff (max 30s).
"""
import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from loguru import logger

from backend.config import get_settings

router = APIRouter(tags=["WebSocket"])
settings = get_settings()


async def _authenticate_ws(ws: WebSocket, token: str | None) -> bool:
    """Authenticate WebSocket connection via JWT query param.

    Usage: ws://host/ws/jobs/123?token=<jwt_access_token>
    Returns True if authenticated, False (and closes WS) if not.
    """
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return False
    try:
        from backend.dependencies import decode_token
        payload = decode_token(token)
        if payload.get("type") != "access":
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return False
        return True
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return False


# ---------------------------------------------------------------------------
# Connection managers
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Manages active WebSocket connections per channel."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if channel in self.active:
            self.active[channel] = [w for w in self.active[channel] if w != ws]

    async def broadcast(self, channel: str, data: dict):
        dead = []
        for ws in self.active.get(channel, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        # Cleanup dead connections
        for ws in dead:
            self.disconnect(channel, ws)


job_manager = ConnectionManager()
project_manager = ConnectionManager()
log_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Redis Pub/Sub Listener
# ---------------------------------------------------------------------------

async def _redis_subscriber(channel: str, ws: WebSocket, manager: ConnectionManager):
    """Subscribe to a Redis pub/sub channel and forward messages to WebSocket.

    Runs as an asyncio task alongside the WebSocket receive loop.
    """
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await ws.send_json(data)
                except Exception:
                    break

        await pubsub.unsubscribe(channel)
        await r.close()
    except ImportError:
        # redis.asyncio not available, fall back to polling
        logger.debug("redis.asyncio not available, WebSocket will use polling mode")
    except Exception as e:
        logger.debug(f"Redis subscriber for {channel} ended: {e}")


# ---------------------------------------------------------------------------
# WS /ws/jobs/{job_id}
# ---------------------------------------------------------------------------

@router.websocket("/ws/jobs/{job_id}")
async def ws_job_progress(ws: WebSocket, job_id: str, token: str = Query(default="")):
    """Real-time progress for a specific job.

    Subscribes to Redis pub/sub channel job:{job_id}.
    Streams: { job_id, progress_pct, current_step, total_steps, eta_seconds, status }
    Connect with: ws://host/ws/jobs/{id}?token=<jwt>
    """
    if not await _authenticate_ws(ws, token):
        return
    await job_manager.connect(job_id, ws)

    # Start Redis subscriber in background
    redis_channel = f"job:{job_id}"
    sub_task = asyncio.create_task(_redis_subscriber(redis_channel, ws, job_manager))

    try:
        while True:
            # Keep connection alive and handle client pings
            data = await ws.receive_text()
            # Client can send heartbeat or commands
            if data == "ping":
                await ws.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        pass
    finally:
        sub_task.cancel()
        job_manager.disconnect(job_id, ws)


# ---------------------------------------------------------------------------
# WS /ws/projects/{project_id}
# ---------------------------------------------------------------------------

@router.websocket("/ws/projects/{project_id}")
async def ws_project_events(ws: WebSocket, project_id: str, token: str = Query(default="")):
    """Project-level events: state changes, handoffs, new assets.

    Subscribes to Redis pub/sub channel project:{project_id}.
    Streams: { event_type, payload, timestamp }
    Connect with: ws://host/ws/projects/{id}?token=<jwt>
    """
    if not await _authenticate_ws(ws, token):
        return
    await project_manager.connect(project_id, ws)

    redis_channel = f"project:{project_id}"
    sub_task = asyncio.create_task(_redis_subscriber(redis_channel, ws, project_manager))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        pass
    finally:
        sub_task.cancel()
        project_manager.disconnect(project_id, ws)


# ---------------------------------------------------------------------------
# WS /ws/notifications (user-level real-time notifs)
# ---------------------------------------------------------------------------

@router.websocket("/ws/notifications")
async def ws_user_notifications(ws: WebSocket, token: str = Query(default=""), user_id: str = Query(default="")):
    """Real-time notifications for the authenticated user.

    Subscribes to Redis pub/sub channel user:{user_id}:notifications.
    Streams: { type: "notification", notification, timestamp }
    Connect with: ws://host/ws/notifications?token=<jwt>&user_id=<uid>
    """
    if not await _authenticate_ws(ws, token):
        return
    if not user_id:
        # Fallback: allow without explicit uid (client can filter)
        user_id = "broadcast"
    channel = f"user:{user_id}:notifications"
    await job_manager.connect(channel, ws)  # reuse manager ok for notifs

    sub_task = asyncio.create_task(_redis_subscriber(channel, ws, job_manager))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        pass
    finally:
        sub_task.cancel()
        job_manager.disconnect(channel, ws)


# ---------------------------------------------------------------------------
# WS /ws/logs
# ---------------------------------------------------------------------------

@router.websocket("/ws/logs")
async def ws_logs(ws: WebSocket, token: str = Query(default="")):
    """Live log stream for authenticated users.

    Subscribes to Redis pub/sub channel logs.
    Streams: { timestamp, level, message, trace_id, job_id, project_id }
    Connect with: ws://host/ws/logs?token=<jwt>
    """
    if not await _authenticate_ws(ws, token):
        return
    await log_manager.connect("logs", ws)

    sub_task = asyncio.create_task(_redis_subscriber("logs", ws, log_manager))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        pass
    finally:
        sub_task.cancel()
        log_manager.disconnect("logs", ws)


# ---------------------------------------------------------------------------
# Helper: Publish events from application code
# ---------------------------------------------------------------------------

async def publish_project_event(project_id: str, event_type: str, payload: dict):
    """Publish a project event to Redis for WebSocket streaming."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        data = json.dumps({
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await r.publish(f"project:{project_id}", data)
        await r.close()
    except Exception as e:
        logger.warning(f"Failed to publish project event: {e}")


async def publish_log_entry(
    level: str, message: str,
    trace_id: str | None = None,
    job_id: str | None = None,
    project_id: str | None = None,
):
    """Publish a log entry to Redis for WebSocket streaming."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        data = json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "trace_id": trace_id,
            "job_id": job_id,
            "project_id": project_id,
        })
        await r.publish("logs", data)
        await r.close()
    except Exception as e:
        logger.warning(f"Failed to publish log entry: {e}")


async def publish_notification_event(user_id: str, notification: dict):
    """Publish a notification event to Redis for WebSocket streaming to the user."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL)
        data = json.dumps({
            "type": "notification",
            "user_id": user_id,
            "notification": notification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await r.publish(f"user:{user_id}:notifications", data)
        await r.close()
    except Exception as e:
        logger.warning(f"Failed to publish notification event: {e}")

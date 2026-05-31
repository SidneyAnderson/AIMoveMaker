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


async def _authenticate_ws(ws: WebSocket, token: str | None) -> dict | None:
    """Authenticate WebSocket connection via JWT query param.

    Returns the decoded payload (with user info) if valid, else None (and closes WS).
    """
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        from backend.dependencies import decode_token
        payload = decode_token(token)
        if payload.get("type") != "access":
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        return payload
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


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

# Simple in-memory presence for collaboration (low-pri feature)
# project_id -> list of active users
presence: dict[str, list[dict]] = {}


def _get_user_from_payload(payload: dict) -> dict:
    """Extract minimal user info for presence/cursors from JWT payload."""
    return {
        "id": payload.get("sub") or payload.get("user_id"),
        "email": payload.get("email", "unknown"),
        "full_name": payload.get("full_name") or payload.get("name") or payload.get("email", "User"),
    }


class PresenceManager:
    """Lightweight presence tracking + broadcast for a project."""

    def add(self, project_id: str, user: dict):
        presence.setdefault(project_id, [])
        # Avoid duplicates
        if not any(u["id"] == user["id"] for u in presence[project_id]):
            presence[project_id].append({**user, "last_active": datetime.now(timezone.utc).isoformat()})
        return presence[project_id]

    def remove(self, project_id: str, user_id: str):
        if project_id in presence:
            presence[project_id] = [u for u in presence[project_id] if u["id"] != user_id]
            if not presence[project_id]:
                del presence[project_id]
        return presence.get(project_id, [])

    def get(self, project_id: str):
        return presence.get(project_id, [])

    async def broadcast_update(self, project_id: str):
        users = self.get(project_id)
        await project_manager.broadcast(project_id, {
            "type": "presence_update",
            "users": users,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


presence_manager = PresenceManager()


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
    payload = await _authenticate_ws(ws, token)
    if not payload:
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
    """Project-level events + real-time collaboration (presence + cursors for gap #9).

    Supports:
    - Redis project events
    - Client messages: {"type": "presence:join"} (auto on connect), {"type": "cursor_move", "x": 0.5, "y": 0.3, ...}
    - Broadcasts: presence_update, cursor_move (for other clients)
    """
    payload = await _authenticate_ws(ws, token)
    if not payload:
        return

    user = _get_user_from_payload(payload)
    await project_manager.connect(project_id, ws)

    # --- Presence join on connect (collaboration feature) ---
    current_users = presence_manager.add(project_id, user)
    await presence_manager.broadcast_update(project_id)

    redis_channel = f"project:{project_id}"
    sub_task = asyncio.create_task(_redis_subscriber(redis_channel, ws, project_manager))

    try:
        while True:
            raw = await ws.receive_text()
            if raw == "ping":
                await ws.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                continue

            try:
                msg = json.loads(raw)
                msg_type = msg.get("type")

                if msg_type == "presence:leave":
                    presence_manager.remove(project_id, user["id"])
                    await presence_manager.broadcast_update(project_id)

                elif msg_type == "cursor_move":
                    # Broadcast cursor position to everyone else in the project (including sender for echo if wanted)
                    await project_manager.broadcast(project_id, {
                        "type": "cursor_move",
                        "user": user,
                        "x": msg.get("x"),
                        "y": msg.get("y"),
                        "view": msg.get("view", "timeline"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                elif msg_type == "presence:join":
                    # Re-broadcast current list (idempotent)
                    await presence_manager.broadcast_update(project_id)

            except Exception:
                # Ignore bad client messages
                pass

    except WebSocketDisconnect:
        pass
    finally:
        sub_task.cancel()
        project_manager.disconnect(project_id, ws)
        # Leave presence
        presence_manager.remove(project_id, user["id"])
        await presence_manager.broadcast_update(project_id)


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
    payload = await _authenticate_ws(ws, token)
    if not payload:
        return
    if not user_id:
        # Fallback: allow without explicit uid (client can filter)
        user_id = payload.get("sub") or payload.get("user_id") or "broadcast"
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
    payload = await _authenticate_ws(ws, token)
    if not payload:
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

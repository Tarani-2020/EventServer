import asyncio
import json
import uuid
from aiohttp import web, WSMsgType

events = {}
pending_responses = {}


# =========================
# WebSocket Handler
# =========================
async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)

                # Registrierung
                if data["type"] == "register":
                    events[data["eventId"]] = {
                        "password": data["password"],
                        "ws": ws
                    }
                    print("Registered event:", data["eventId"])

                # Antwort vom Client-Server
                elif data["type"] == "response":
                    request_id = data["requestId"]
                    if request_id in pending_responses:
                        future = pending_responses.pop(request_id)
                        future.set_result(data["result"])

    finally:
        # Cleanup bei Disconnect
        for event_id, entry in list(events.items()):
            if entry["ws"] is ws:
                del events[event_id]

    return ws


# =========================
# HTTP Event Endpoint
# =========================
async def event_handler(request):
    body = await request.json()

    event_id = body.get("eventId")
    password = body.get("password")
    data = body.get("data")

    entry = events.get(event_id)
    if not entry or entry["password"] != password:
        return web.json_response(
            {"error": "Invalid event or password"},
            status=403
        )

    request_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    pending_responses[request_id] = future

    await entry["ws"].send_json({
        "type": "event",
        "requestId": request_id,
        "data": data
    })

    try:
        result = await asyncio.wait_for(future, timeout=10)
        return web.json_response(result)
    except asyncio.TimeoutError:
        pending_responses.pop(request_id, None)
        return web.json_response(
            {"error": "Timeout"},
            status=504
        )


# =========================
# App Setup
# =========================
app = web.Application()
app.router.add_get("/ws", ws_handler)
app.router.add_post("/event", event_handler)

web.run_app(app, port=8080)

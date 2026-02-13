import time
from aiohttp import web, ClientSession

events = {}

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
  <title>Event auslösen</title>
</head>
<body>
  <h2>Passwort eingeben</h2>
  <form method="GET">
    <input type="password" name="password" autofocus />
    <button type="submit">Event auslösen</button>
  </form>
</body>
</html>
"""

# =========================
# Update / Heartbeat
# =========================
async def update_handler(request):
    body = await request.json()

    event_id = body["eventId"]
    events[event_id] = {
        "password": body["password"],
        "callback": body["callback"],
        "last_seen": time.time()
    }

    print(f"[UPDATE] {event_id} → {body['callback']}")
    return web.json_response({"status": "updated"})


# =========================
# Trigger (GET)
# =========================
async def trigger_handler(request):
    event_id = request.match_info["eventId"]
    password = (
      request.match_info.get("password")
      or request.query.get("password")
    )

    entry = events.get(event_id)
    if not entry:
        return web.Response(text="Event nicht registriert", status=404)

    # Passwort fehlt → Formular anzeigen
    if not password:
        return web.Response(text=HTML_FORM, content_type="text/html")

    if password != entry["password"]:
        return web.Response(text="Falsches Passwort", status=403)

    try:
        async with ClientSession() as session:
            async with session.post(
                entry["callback"],
                json={"eventId": event_id}
            ):
                pass

        age = int(time.time() - entry["last_seen"])
        return web.Response(
            text=f"Event ausgelöst ✅ (letztes Update vor {age}s)"
        )

    except Exception as e:
        return web.Response(
            text=f"Callback nicht erreichbar ❌\n{e}",
            status=502
        )


# =========================
# App Setup
# =========================
app = web.Application()
app.router.add_post("/update", update_handler)
app.router.add_get("/e/{eventId}", trigger_handler)
app.router.add_get("/e/{eventId}/{password}", trigger_handler)

web.run_app(app, port=8080)
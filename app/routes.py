from flask import Blueprint, Response, redirect
from nyct_gtfs import NYCTFeed
from datetime import datetime, timedelta, timezone
import os
import json

from app.alerts import get_alerts_status

bp = Blueprint("main", __name__)

# Stop IDs
STOP_IDS = {
    "Q": {"S": "Q03S", "N": "Q03N"},     # 72nd St
    "6": {"S": "627S", "N": "627N"}      # 77th St
}

NUM_TRAINS = int(os.getenv("NUM_TRAINS", "8"))

# Load both feeds
FEEDS = {
    "Q": NYCTFeed("Q"),
    "6": NYCTFeed("6")
}

REFRESH_TTL = timedelta(seconds=20)
LAST_REFRESH = datetime.min
LAST_RESPONSE_DATA = None
LAST_RESPONSE_AT = None

def get_upcoming_trains(feed, stop_id, num_trains=NUM_TRAINS):
    now = datetime.now()
    upcoming = []
    for trip in feed.trips:
        for update in trip.stop_time_updates:
            if update.stop_id == stop_id and update.arrival and update.arrival > now:
                minutes_until = int((update.arrival - now).total_seconds() / 60)
                upcoming.append({
                    "destination": trip.headsign_text,
                    "direction": trip.direction,
                    "minutes_until": minutes_until
                })
    upcoming.sort(key=lambda x: x["minutes_until"])
    return upcoming[:num_trains]

def build_output():
    output = {}
    for line, directions in STOP_IDS.items():
        feed = FEEDS[line]
        for direction, stop_id in directions.items():
            key = f"{line}_{direction}"
            output[key] = get_upcoming_trains(feed, stop_id)
    return output

def build_response_payload(output, now, is_stale, status):
    cache_age_s = 0
    if LAST_RESPONSE_AT:
        cache_age_s = int((now - LAST_RESPONSE_AT).total_seconds())

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "cache_age_s": cache_age_s,
            "is_stale": is_stale,
        },
        "status": status,
    }
    payload.update(output)
    return payload

@bp.route("/health")
def health():
    now = datetime.now()
    cache_age = None
    if LAST_RESPONSE_AT:
        cache_age = int((now - LAST_RESPONSE_AT).total_seconds())

    payload = {
        "status": "ok",
        "cache_age_seconds": cache_age,
        "last_refresh": None if LAST_REFRESH == datetime.min else LAST_REFRESH.isoformat()
    }
    response_data = json.dumps(payload)
    response = Response(response_data, content_type="application/json")
    response.headers["Content-Length"] = str(len(response_data))
    response.headers["Connection"] = "close"
    response.headers["Content-Encoding"] = "identity"
    response.headers["Cache-Control"] = "no-store"
    response.direct_passthrough = False
    return response

@bp.route("/")
def index():
    return redirect("/health", code=302)

@bp.route("/next_trains")
def next_trains():
    global LAST_REFRESH, LAST_RESPONSE_DATA, LAST_RESPONSE_AT

    try:
        now = datetime.now()
        if now - LAST_REFRESH >= REFRESH_TTL:
            for feed in FEEDS.values():
                feed.refresh()
            LAST_REFRESH = now

        # Build output only for southbound directions
        output = build_output()
        status = get_alerts_status(now)
        LAST_RESPONSE_DATA = output
        LAST_RESPONSE_AT = now
        response_payload = build_response_payload(output, now, False, status)
        response_data = json.dumps(response_payload)

        # Build proper JSON response
        response = Response(response_data, content_type="application/json")
        response.headers["Content-Length"] = str(len(response_data))
        response.headers["Connection"] = "close"
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Cache"] = "miss"
        response.direct_passthrough = False
        return response

    except Exception as e:
        if LAST_RESPONSE_DATA:
            now = datetime.now()
            status = get_alerts_status(now)
            response_payload = build_response_payload(LAST_RESPONSE_DATA, now, True, status)
            response_data = json.dumps(response_payload)
            response = Response(response_data, content_type="application/json")
            response.headers["Content-Length"] = str(len(response_data))
            response.headers["Connection"] = "close"
            response.headers["Content-Encoding"] = "identity"
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Cache"] = "stale"
            response.headers["X-Cache-Age-Seconds"] = str(
                int((now - LAST_RESPONSE_AT).total_seconds())
            )
            response.direct_passthrough = False
            return response, 200

        error_data = json.dumps({"error": str(e)})
        response = Response(error_data, content_type="application/json")
        response.headers["Content-Length"] = str(len(error_data))
        response.headers["Connection"] = "close"
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.direct_passthrough = False
        return response, 500

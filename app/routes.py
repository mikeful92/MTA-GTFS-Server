from flask import Blueprint, Response
from nyct_gtfs import NYCTFeed
from datetime import datetime, timedelta
import json

bp = Blueprint("main", __name__)

# Southbound stop IDs
STOP_IDS = {
    "Q": {"S": "Q03S"},     # 72nd St
    "6": {"S": "627S"}      # 103rd St
}

NUM_TRAINS = 3

# Load both feeds
FEEDS = {
    "Q": NYCTFeed("Q"),
    "6": NYCTFeed("6")
}

REFRESH_TTL = timedelta(seconds=20)
LAST_REFRESH = datetime.min
LAST_RESPONSE = None
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
        stop_id = directions["S"]
        key = f"{line}_S"
        output[key] = get_upcoming_trains(feed, stop_id)
    return output

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

@bp.route("/next_trains")
def next_trains():
    global LAST_REFRESH, LAST_RESPONSE, LAST_RESPONSE_AT

    try:
        now = datetime.now()
        if now - LAST_REFRESH >= REFRESH_TTL:
            for feed in FEEDS.values():
                feed.refresh()
            LAST_REFRESH = now

        # Build output only for southbound directions
        output = build_output()
        LAST_RESPONSE = json.dumps(output)
        LAST_RESPONSE_AT = now

        # Build proper JSON response
        response = Response(LAST_RESPONSE, content_type="application/json")
        response.headers["Content-Length"] = str(len(LAST_RESPONSE))
        response.headers["Connection"] = "close"
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Cache"] = "miss"
        response.direct_passthrough = False
        return response

    except Exception as e:
        if LAST_RESPONSE:
            response = Response(LAST_RESPONSE, content_type="application/json")
            response.headers["Content-Length"] = str(len(LAST_RESPONSE))
            response.headers["Connection"] = "close"
            response.headers["Content-Encoding"] = "identity"
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Cache"] = "stale"
            response.headers["X-Cache-Age-Seconds"] = str(
                int((datetime.now() - LAST_RESPONSE_AT).total_seconds())
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

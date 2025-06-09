from flask import Blueprint, jsonify, Response
from nyct_gtfs import NYCTFeed
from datetime import datetime
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

@bp.route("/next_trains")
def next_trains():
    try:
        # Refresh both Q and 6 feeds
        for feed in FEEDS.values():
            feed.refresh()

        # Build output only for southbound directions
        output = {}
        for line, directions in STOP_IDS.items():
            feed = FEEDS[line]
            stop_id = directions["S"]
            key = f"{line}_S"
            output[key] = get_upcoming_trains(feed, stop_id)

        # Build proper JSON response
        response_data = json.dumps(output)
        response = Response(response_data, content_type="application/json")
        response.headers["Content-Length"] = str(len(response_data))
        response.headers["Connection"] = "close"
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.direct_passthrough = False
        return response

    except Exception as e:
        error_data = json.dumps({"error": str(e)})
        response = Response(error_data, content_type="application/json")
        response.headers["Content-Length"] = str(len(error_data))
        response.headers["Connection"] = "close"
        response.headers["Content-Encoding"] = "identity"
        response.headers["Cache-Control"] = "no-store"
        response.direct_passthrough = False
        return response, 500

from flask import Blueprint, jsonify
from nyct_gtfs import NYCTFeed
from datetime import datetime

bp = Blueprint('main', __name__)

STOP_IDS = {"Q": {"N": "Q03N", "S": "Q03S"}}
NUM_TRAINS = 3
feed = NYCTFeed("Q")

def get_upcoming_trains(feed, stop_id, num_trains=NUM_TRAINS):
    now = datetime.now()
    upcoming = []
    for trip in feed.trips:
        for update in trip.stop_time_updates:
            if update.stop_id == stop_id and update.arrival and update.arrival > now:
                upcoming.append({
                    "arrival_time": update.arrival.isoformat(),
                    "destination": trip.headsign_text,  # Correct!
                    "direction": trip.direction
                })
    upcoming.sort(key=lambda x: x["arrival_time"])
    return upcoming[:num_trains]

@bp.route('/next_trains')
def next_trains():
    try:
        feed.refresh()
        return jsonify({d: get_upcoming_trains(feed, stop) for d, stop in STOP_IDS["Q"].items()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

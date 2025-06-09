from flask import Blueprint, jsonify, request
from nyct_gtfs import NYCTFeed
from datetime import datetime

bp = Blueprint('main', __name__)

STOP_IDS = {
    "Q": {"N": "Q03N", "S": "Q03S"},
    "6": {"N": "635N", "S": "635S"}  # Optional: add other lines if needed
}
NUM_TRAINS = 3
feed = NYCTFeed("Q")  # Change if you're rotating multiple feeds

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

@bp.route('/next_trains')
def next_trains():
    try:
        # Query params: line (default Q), direction (N/S), num_trains (default 3)
        line = request.args.get("line", "Q")
        direction = request.args.get("direction")  # Optional
        num_trains = int(request.args.get("num_trains", NUM_TRAINS))

        if line not in STOP_IDS:
            return jsonify({"error": "Invalid line"}), 400

        feed.refresh()

        if direction:
            stop_id = STOP_IDS[line].get(direction.upper())
            if not stop_id:
                return jsonify({"error": "Invalid direction"}), 400
            trains = get_upcoming_trains(feed, stop_id, num_trains)
            return jsonify(trains)
        else:
            data = {
                d: get_upcoming_trains(feed, stop_id, num_trains)
                for d, stop_id in STOP_IDS[line].items()
            }
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

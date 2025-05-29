from flask import Flask, jsonify
from nyct_gtfs import NYCTFeed
from datetime import datetime

app = Flask(__name__)

# Configuration
STOP_IDS = {
    "Q": {"N": "Q03N", "S": "Q03S"}  # Replace with your station's stop IDs
}
NUM_TRAINS = 3  # Number of upcoming trains to return

# Initialize GTFS feeds
feeds = {
    "Q": NYCTFeed("Q")  # No API key required
}

def get_upcoming_trains(feed, stop_id, num_trains=NUM_TRAINS):
    now = datetime.now()
    upcoming = []

    for trip in feed.trips:
        for update in trip.stop_time_updates:
            if update.stop_id == stop_id:
                arrival_time = update.arrival
                if arrival_time and arrival_time > now:
                    upcoming.append({
                        "arrival_time": arrival_time.isoformat(),
                        "destination": trip.trip_headsign,
                        "direction": trip.direction
                    })

    upcoming.sort(key=lambda x: x["arrival_time"])
    return upcoming[:num_trains]

@app.route('/next_trains')
def next_trains():
    response = {}
    try:
        feed = feeds["Q"]
        feed.refresh()

        for direction, stop_id in STOP_IDS["Q"].items():
            response[direction] = get_upcoming_trains(feed, stop_id)

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
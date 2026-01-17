# MTA GTFS Flask Server

A small Flask service that provides real-time next-train arrivals and per-line service status badges for the MTA Q and 6 lines. It uses the `nyct-gtfs` library for GTFS-RT trip updates and a separate GTFS-RT Service Alerts feed to summarize line status.

## Features
- `/next_trains` endpoint returns arrivals for Q and 6 (N/S directions) plus status badges.
- In-memory caching for arrivals with a short TTL and stale fallback on upstream errors.
- Separate in-memory caching for Service Alerts with its own TTL, retry/backoff, and stale fallback.
- `/health` endpoint for lightweight liveness and cache age checks.

## API

### GET /next_trains
Returns upcoming train arrivals plus a per-line status summary.

Response shape:
```
{
  "meta": {
    "generated_at": "ISO-8601 UTC",
    "cache_age_s": 0,
    "is_stale": false
  },
  "status": {
    "Q": {"badge": "OT|DLY|CHG|PLN|UNK", "reason": "optional <= 40 chars"},
    "6": {"badge": "OT|DLY|CHG|PLN|UNK", "reason": "optional <= 40 chars"}
  },
  "Q_S": [{"destination": "...", "direction": "S", "minutes_until": 12}, ...],
  "Q_N": [...],
  "6_S": [...],
  "6_N": [...]
}
```

Badge meanings:
- `OT`: on time (no relevant alerts)
- `DLY`: delays or disruptions
- `CHG`: service change, reroute, bypass, or skip
- `PLN`: planned work or maintenance
- `UNK`: status unknown (alerts unavailable)

Notes:
- `meta.cache_age_s` reflects the age of the cached arrivals payload (if available).
- `meta.is_stale` is `true` when serving cached arrivals due to an upstream error.
- `status.*.reason` is optional and truncated to 40 characters.

### GET /health
Returns server health and cache metadata.

Response shape:
```
{
  "status": "ok",
  "cache_age_seconds": 0,
  "last_refresh": "ISO-8601 or null"
}
```

## Caching and Refresh Behavior

### Arrivals cache
- Cached in memory with a refresh TTL (currently 20 seconds).
- If the upstream refresh fails, the server returns the last cached arrivals and marks the response as stale.

### Service Alerts cache
- Cached in memory with `ALERTS_TTL_S` (default 120 seconds).
- One retry with a small backoff (0.5s) and a 4s request timeout.
- If fetch fails, cached alerts are used when available; otherwise status becomes `UNK`.

## Configuration

Environment variables:
- `NUM_TRAINS` (default `8`): number of upcoming trains per direction.
- `ALERTS_TTL_S` (default `120`): Service Alerts cache TTL in seconds.
- `MTA_ALERTS_URL` (optional): override the Service Alerts GTFS-RT URL.

Defaults:
- Service Alerts URL: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts`

## Setup

1) Clone the repo
2) Create a virtual environment and install requirements
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running Locally

```
export NUM_TRAINS=8
python run.py
```

The server will start on the default Flask host/port (see `run.py`).

## Testing

```
source venv/bin/activate
pytest -v
```

Tests do not require live network calls; alerts fetches are mocked in unit tests.

## Project Structure
- `app/routes.py`: Flask routes and arrivals caching
- `app/alerts.py`: Service Alerts fetch, caching, and status computation
- `app/helpers/line_status_utils.py`: helper utilities (unused by default)
- `tests/`: pytest suite

## Notes
- This service targets PythonAnywhere; keep Python version compatibility in mind.
- Network failures should never break `/next_trains`; at worst, status becomes `UNK`.

## License

Add license information here if applicable.

# MTA GTFS Flask Server

## What this is
A small Flask service that provides real-time next-train arrivals and per-line status for the MTA Q and 6 lines.

Endpoints:
- `/next_trains`: arrivals plus status badges
- `/health`: cache/refresh status
- `/`: redirects to `/health`

Caching strategy:
- Arrivals cache TTL: 20 seconds, with stale fallback on upstream errors.
- Alerts cache TTL: `ALERTS_TTL_S` (default 120 seconds), with stale fallback if alerts fetch fails.

## API

### GET /next_trains
Example response shape:
```
{
  "meta": {
    "generated_at": "2026-01-17T19:58:30Z",
    "cache_age_s": 0,
    "is_stale": false
  },
  "status": {
    "Q": {"badge": "OT", "reason": "optional <= 40 chars"},
    "6": {"badge": "DLY", "reason": "optional <= 40 chars"}
  },
  "Q_S": [{"destination": "...", "direction": "S", "minutes_until": 12}],
  "Q_N": [{"destination": "...", "direction": "N", "minutes_until": 5}],
  "6_S": [{"destination": "...", "direction": "S", "minutes_until": 3}],
  "6_N": [{"destination": "...", "direction": "N", "minutes_until": 10}]
}
```

Status badges:
- `OT`: on time (no relevant alerts)
- `DLY`: delays or disruptions
- `CHG`: service change, reroute, bypass, or skip
- `PLN`: planned work or maintenance
- `UNK`: status unknown (alerts unavailable)

Meta fields:
- `generated_at`: ISO-8601 UTC timestamp
- `cache_age_s`: age of cached arrivals payload in seconds (0 if none)
- `is_stale`: `true` when serving cached arrivals due to an error

### GET /health
Returns cache age and last refresh time.

## Local development (WSL/Linux/macOS)

PythonAnywhere max Python version is 3.10. Use Python 3.10 locally for consistency.

Clone and install:
```
git clone <repo-url>
cd MTA-GTFS-Server
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run locally:
```
source venv/bin/activate
python run.py
```

Run tests:
```
source venv/bin/activate
pytest -v
```

Tests should not require network access. If they do, mock the network or ensure the alerts fetch is patched in tests.

Example local verification:
```
curl -s http://127.0.0.1:5000/health
curl -s http://127.0.0.1:5000/next_trains | head -c 400
```

## Configuration (Environment variables)

| Name | Default | Purpose | Example |
| --- | --- | --- | --- |
| `NUM_TRAINS` | `8` | Number of upcoming trains per direction | `NUM_TRAINS=6` |
| `ALERTS_TTL_S` | `120` | Alerts cache TTL in seconds | `ALERTS_TTL_S=180` |
| `MTA_ALERTS_URL` | default Service Alerts URL | Override alerts feed URL | `MTA_ALERTS_URL=https://...` |

Arrivals cache TTL is currently a constant in code (20 seconds).

If you use an MTA API key in your environment, set it in the Web tab on PythonAnywhere (name it per your WSGI/config usage). If no key is required, leave unset.

## Deployment on PythonAnywhere (step-by-step runbook)

1) Log in to PythonAnywhere
- Go to https://www.pythonanywhere.com and open your Dashboard.

2) Open a Bash console
- Dashboard → “Consoles” → “Bash”.

3) Locate the project directory
- Typical path: `/home/<username>/MTA-GTFS-Server`
- If unsure:
```
ls ~/
```

4) Update code
```
cd /home/<username>/MTA-GTFS-Server
git status
git pull
```

5) Create or reuse a virtualenv (Python 3.10)
```
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

6) Set environment variables
- Go to the Web tab → “Environment variables”.
- Add/edit `NUM_TRAINS`, `ALERTS_TTL_S`, `MTA_ALERTS_URL` as needed.
- If you use an API key, set it here as well.

7) Reload the web app
- Web tab → click “Reload”.

8) Verify deployment
From PythonAnywhere Bash:
```
curl -s https://mikeful92.pythonanywhere.com/health
curl -s https://mikeful92.pythonanywhere.com/next_trains | head -c 400
```
From your local machine:
```
curl -s https://mikeful92.pythonanywhere.com/health
curl -s https://mikeful92.pythonanywhere.com/next_trains | head -c 400
```
Healthy looks like:
- `/health` returns `{"status":"ok", ...}`
- `/next_trains` returns JSON with `meta`, `status`, `Q_S`, `Q_N`, `6_S`, `6_N`

### Common update routine
1) Open PythonAnywhere Bash console
2) `cd /home/<username>/MTA-GTFS-Server`
3) `git status` and `git pull`
4) `source venv/bin/activate`
5) `pip install -r requirements.txt`
6) Update env vars in Web tab if needed
7) Web tab → Reload
8) `curl -s https://mikeful92.pythonanywhere.com/health`

## Troubleshooting

### /next_trains returns 500
- Check logs: Web tab → “Logs” → error log and server log.
- Look for stack traces referencing `app/routes.py` or alerts fetch.

### MTA endpoint not reachable / DNS issues
- Server returns cached arrivals when available.
- `status` badges become `UNK` if alerts cannot be fetched and no cached alerts exist.
- Check error log for DNS or connection errors.

### Changes not showing up
- Confirm you pulled the right branch.
- Confirm you are in `/home/<username>/MTA-GTFS-Server`.
- Web tab → click “Reload”.

### Alerts show UNK
- Alerts feed unreachable or did not match route IDs.
- Check error log for alerts fetch failures.
- Confirm `MTA_ALERTS_URL` and network access.

### Cache age is high / is_stale=true
- Upstream refresh failed or network is blocked.
- Check Web tab logs for exceptions.

## Maintenance
- Rotate keys: update environment variables in the Web tab.
- Update dependencies: `pip install -r requirements.txt` after bumping versions.
- Safe rollback:
```
cd /home/<username>/MTA-GTFS-Server
git checkout <previous-commit>
```
Then Web tab → Reload.

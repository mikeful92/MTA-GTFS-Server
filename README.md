# MTA GTFS Flask Server

This Flask app provides real-time next train arrivals for the MTA Q line, processed from GTFS data using the nyct-gtfs library.

TODO: keep Python version consistent with PythonAnywhere (max 3.10).

## Setup
1. Clone the repo
2. Create virtual environment & install requirements
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## /next_trains status
The response includes a `status` object with per-line badges:

- `OT`: on time
- `DLY`: delays or disruptions
- `CHG`: service change, reroute, bypass, or skip
- `PLN`: planned work or maintenance
- `UNK`: status unknown (alerts unavailable)

Alerts are sourced from the MTA GTFS-RT Service Alerts feed and cached separately.

- `ALERTS_TTL_S` (default `120`): alerts cache TTL in seconds
- `MTA_ALERTS_URL` (optional): override the Service Alerts feed URL

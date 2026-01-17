import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nyct_gtfs.compiled_gtfs import gtfs_realtime_pb2

from app import alerts

def _make_alert(route_id, header_text):
    feed = gtfs_realtime_pb2.FeedMessage()
    entity = feed.entity.add()
    entity.id = "1"
    alert = entity.alert
    informed = alert.informed_entity.add()
    informed.route_id = route_id
    alert.header_text.translation.add(text=header_text)
    return feed

def test_compute_status_delay_for_q():
    feed = _make_alert("Q", "Q trains are delayed due to signal problems")
    status = alerts.compute_status_from_alerts(feed)
    assert status["Q"]["badge"] == "DLY"
    assert status["6"]["badge"] == "OT"

def test_compute_status_planned_work():
    feed = _make_alert("6", "Planned work affects 6 trains")
    status = alerts.compute_status_from_alerts(feed)
    assert status["6"]["badge"] == "PLN"

def test_compute_status_service_change():
    feed = _make_alert("Q", "Service change: Q trains rerouted")
    status = alerts.compute_status_from_alerts(feed)
    assert status["Q"]["badge"] == "CHG"

def test_alerts_cache_used_on_fetch_failure(monkeypatch):
    cached_feed = _make_alert("Q", "Q trains are delayed")
    monkeypatch.setattr(alerts, "CACHED_ALERTS", cached_feed)
    monkeypatch.setattr(alerts, "LAST_ALERTS_REFRESH", datetime.now() - timedelta(seconds=999))
    monkeypatch.setattr(alerts, "ALERTS_TTL_S", 0)

    def _fail_fetch(url):
        raise RuntimeError("fetch failed")

    monkeypatch.setattr(alerts, "fetch_alerts_feed", _fail_fetch)
    status = alerts.get_alerts_status(datetime.now())
    assert status["Q"]["badge"] == "DLY"

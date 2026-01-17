import os
import time
from datetime import datetime, timedelta

import requests
from nyct_gtfs.compiled_gtfs import gtfs_realtime_pb2

DEFAULT_ALERTS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts"

ALERTS_TTL_S = int(os.getenv("ALERTS_TTL_S", "120"))
MTA_ALERTS_URL = os.getenv("MTA_ALERTS_URL", DEFAULT_ALERTS_URL)

LAST_ALERTS_REFRESH = datetime.min
CACHED_ALERTS = None

DELAY_KEYWORDS = (
    "delay",
    "delays",
    "signal problem",
    "signal problems",
    "congestion",
    "slow",
    "medical emergency",
    "police activity",
)
CHANGE_KEYWORDS = (
    "service change",
    "reroute",
    "rerouted",
    "bypass",
    "bypassing",
    "skip",
    "skipping",
    "expressed",
    "detour",
    "shuttle",
)
PLANNED_KEYWORDS = (
    "planned work",
    "maintenance",
    "construction",
    "track work",
    "scheduled",
)

BADGE_PRIORITY = {
    "OT": 0,
    "PLN": 1,
    "CHG": 2,
    "DLY": 3,
}

LINE_IDS = {"Q", "6"}

def fetch_alerts_feed(url):
    last_error = None
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=4)
            response.raise_for_status()
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            return feed
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.5)
    raise last_error

def get_alerts_feed(now):
    global LAST_ALERTS_REFRESH, CACHED_ALERTS

    if now - LAST_ALERTS_REFRESH < timedelta(seconds=ALERTS_TTL_S):
        return CACHED_ALERTS

    try:
        feed = fetch_alerts_feed(MTA_ALERTS_URL)
        CACHED_ALERTS = feed
    except Exception:
        feed = None
    finally:
        LAST_ALERTS_REFRESH = now

    return CACHED_ALERTS if feed is None else feed

def _extract_translated_text(translated):
    if not translated or not translated.translation:
        return ""
    return translated.translation[0].text or ""

def _normalize_text(text):
    return " ".join(text.split())

def _truncate_reason(text, max_len=40):
    text = _normalize_text(text)
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3].rstrip() + "..."

def _alert_text(alert):
    header = _extract_translated_text(alert.header_text)
    if header:
        return header
    return _extract_translated_text(alert.description_text)

def _alert_text_combined(alert):
    header = _extract_translated_text(alert.header_text)
    description = _extract_translated_text(alert.description_text)
    if header and description:
        return f"{header} {description}"
    return header or description or ""

def _classify_by_cause_effect(alert):
    if alert.effect == gtfs_realtime_pb2.Alert.Effect.SIGNIFICANT_DELAYS:
        return "DLY"

    if alert.effect in (
        gtfs_realtime_pb2.Alert.Effect.NO_SERVICE,
        gtfs_realtime_pb2.Alert.Effect.REDUCED_SERVICE,
        gtfs_realtime_pb2.Alert.Effect.DETOUR,
        gtfs_realtime_pb2.Alert.Effect.MODIFIED_SERVICE,
        gtfs_realtime_pb2.Alert.Effect.STOP_MOVED,
    ):
        return "CHG"

    if alert.cause in (
        gtfs_realtime_pb2.Alert.Cause.MAINTENANCE,
        gtfs_realtime_pb2.Alert.Cause.CONSTRUCTION,
    ):
        return "PLN"

    if alert.cause in (
        gtfs_realtime_pb2.Alert.Cause.TECHNICAL_PROBLEM,
        gtfs_realtime_pb2.Alert.Cause.ACCIDENT,
        gtfs_realtime_pb2.Alert.Cause.MEDICAL_EMERGENCY,
        gtfs_realtime_pb2.Alert.Cause.POLICE_ACTIVITY,
        gtfs_realtime_pb2.Alert.Cause.WEATHER,
        gtfs_realtime_pb2.Alert.Cause.STRIKE,
        gtfs_realtime_pb2.Alert.Cause.DEMONSTRATION,
    ):
        return "DLY"

    return None

def _classify_alert(alert):
    text = _alert_text_combined(alert)
    lower = text.lower()
    matched_text = False

    if any(keyword in lower for keyword in DELAY_KEYWORDS):
        badge = "DLY"
        matched_text = True
    elif any(keyword in lower for keyword in CHANGE_KEYWORDS):
        badge = "CHG"
        matched_text = True
    elif any(keyword in lower for keyword in PLANNED_KEYWORDS):
        badge = "PLN"
        matched_text = True
    else:
        badge = _classify_by_cause_effect(alert)

    reason = None
    if badge and matched_text:
        reason = _truncate_reason(_alert_text(alert))

    return badge, reason

def _affected_lines(alert):
    lines = set()
    for entity in alert.informed_entity:
        if entity.route_id in LINE_IDS:
            lines.add(entity.route_id)
    return lines

def compute_status_from_alerts(feed):
    if feed is None:
        return {
            "Q": {"badge": "UNK"},
            "6": {"badge": "UNK"},
        }

    status = {
        "Q": {"badge": "OT"},
        "6": {"badge": "OT"},
    }
    reasons = {"Q": None, "6": None}
    priorities = {"Q": 0, "6": 0}

    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        lines = _affected_lines(alert)
        if not lines:
            continue

        badge, reason = _classify_alert(alert)
        if not badge:
            continue
        priority = BADGE_PRIORITY.get(badge, 0)

        for line in lines:
            if priority > priorities[line]:
                status[line]["badge"] = badge
                priorities[line] = priority
                reasons[line] = reason
            elif priority == priorities[line] and reason and not reasons[line]:
                reasons[line] = reason

    for line, reason in reasons.items():
        if reason:
            status[line]["reason"] = reason

    return status

def get_alerts_status(now=None):
    if now is None:
        now = datetime.now()
    feed = get_alerts_feed(now)
    return compute_status_from_alerts(feed)

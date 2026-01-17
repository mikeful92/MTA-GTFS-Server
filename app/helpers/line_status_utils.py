# Helper utilities for computing per-line status badges from alerts/trip delays.
ALLOWED_BADGES = {"OT", "DLY", "CHG", "PLN", "UNK"}

_DELAY_KEYWORDS = (
    "delay",
    "delays",
    "delayed",
    "late",
    "running late",
    "stalled",
    "holding",
)
_PLANNED_KEYWORDS = (
    "planned work",
    "maintenance",
    "track work",
    "construction",
    "signal modernization",
    "weekend work",
    "capital work",
)
_CHANGE_KEYWORDS = (
    "reroute",
    "re-route",
    "bypass",
    "skipping",
    "skip",
    "service change",
    "service changes",
    "detour",
    "diverted",
    "terminating",
    "terminate",
    "turning",
)
_CHANGE_EFFECTS = {
    "DETOUR",
    "MODIFIED_SERVICE",
    "ADDED_SERVICE",
    "REDUCED_SERVICE",
    "NO_SERVICE",
}


def compute_line_status(lines, alerts_by_line, delays_by_line, alerts_available):
    status = {}
    for line in lines:
        badge = "UNK"
        reason = None

        if alerts_available:
            badge, reason = _badge_from_alerts(alerts_by_line.get(line, []))
            if badge is None:
                badge = "OT"
        else:
            if _line_has_delay(delays_by_line.get(line, [])):
                badge = "DLY"
                reason = "Delay reported in trip updates"
            else:
                badge = "UNK"

        entry = {"badge": badge}
        reason = _truncate_reason(reason)
        if reason:
            entry["reason"] = reason
        status[line] = entry

    return status


def extract_alerts_by_line(feeds, lines):
    alerts_by_line = {line: [] for line in lines}
    for line, feed in feeds.items():
        for alert in _iter_feed_alerts(feed):
            normalized = _normalize_alert(alert, fallback_line=line)
            for route_id in normalized["route_ids"]:
                if route_id in alerts_by_line:
                    alerts_by_line[route_id].append(normalized)
    return alerts_by_line


def extract_trip_delays_by_line(feeds):
    delays_by_line = {}
    for line, feed in feeds.items():
        delays = []
        for trip in getattr(feed, "trips", []) or []:
            delay = _extract_trip_delay_seconds(trip)
            if delay is not None:
                delays.append(delay)
        delays_by_line[line] = delays
    return delays_by_line


def _badge_from_alerts(alerts):
    best = None
    best_reason = None
    for alert in alerts:
        badge = _alert_badge(alert)
        if badge is None:
            continue
        if best is None or _badge_priority(badge) < _badge_priority(best):
            best = badge
            best_reason = alert.get("text")
    return best, best_reason


def _alert_badge(alert):
    effect = (alert.get("effect") or "").upper()
    text = (alert.get("text") or "").lower()

    if "DELAY" in effect or _contains_keyword(text, _DELAY_KEYWORDS):
        return "DLY"
    if _contains_keyword(text, _PLANNED_KEYWORDS):
        return "PLN"
    if effect in _CHANGE_EFFECTS or _contains_keyword(text, _CHANGE_KEYWORDS):
        return "CHG"
    return None


def _badge_priority(badge):
    return {"DLY": 0, "PLN": 1, "CHG": 2}.get(badge, 3)


def _line_has_delay(delays):
    for delay in delays:
        try:
            if int(delay) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _normalize_alert(alert, fallback_line):
    payload = _extract_alert_payload(alert)
    header = _translated_text(_get_attr_or_key(payload, "header_text"))
    description = _translated_text(_get_attr_or_key(payload, "description_text"))
    text = " ".join(part for part in (header, description) if part).strip()
    route_ids = _extract_route_ids(payload)
    if not route_ids and fallback_line:
        route_ids = {fallback_line}
    effect = _get_attr_or_key(payload, "effect")
    return {
        "route_ids": route_ids,
        "effect": str(effect) if effect is not None else "",
        "text": text,
    }


def _extract_alert_payload(alert):
    if alert is None:
        return {}
    if isinstance(alert, dict):
        return alert.get("alert", alert)
    nested = getattr(alert, "alert", None)
    return nested if nested is not None else alert


def _iter_feed_alerts(feed):
    alerts = getattr(feed, "alerts", None)
    if alerts is not None:
        return alerts

    feed_message = getattr(feed, "feed", None)
    entities = getattr(feed_message, "entity", None) if feed_message else None
    if entities is None:
        return []

    extracted = []
    for entity in entities:
        alert = getattr(entity, "alert", None)
        if alert is None and isinstance(entity, dict):
            alert = entity.get("alert")
        if alert is not None:
            extracted.append(alert)
    return extracted


def _extract_route_ids(alert_payload):
    route_ids = set()
    entities = _get_attr_or_key(alert_payload, "informed_entity", []) or []
    for entity in entities:
        route_id = _get_attr_or_key(entity, "route_id")
        if not route_id:
            route_id = _get_attr_or_key(entity, "route")
        if route_id:
            route_ids.add(str(route_id))
    return route_ids


def _extract_trip_delay_seconds(trip):
    if trip is None:
        return None

    if isinstance(trip, dict):
        delay = trip.get("delay")
        if delay is not None:
            return delay
        trip_update = trip.get("trip_update", {})
        return trip_update.get("delay")

    delay = getattr(trip, "delay", None)
    if delay is not None:
        return delay

    trip_update = getattr(trip, "trip_update", None)
    if trip_update is not None:
        return getattr(trip_update, "delay", None)

    return None


def _translated_text(value):
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        translations = value.get("translation")
        if isinstance(translations, list):
            texts = [item.get("text") for item in translations if item.get("text")]
            if texts:
                return " ".join(texts)
        text = value.get("text")
        return text if isinstance(text, str) else ""

    translations = getattr(value, "translation", None)
    if translations:
        texts = [getattr(item, "text", None) for item in translations]
        texts = [text for text in texts if text]
        if texts:
            return " ".join(texts)
    text = getattr(value, "text", None)
    return text if isinstance(text, str) else ""


def _get_attr_or_key(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _contains_keyword(text, keywords):
    return any(keyword in text for keyword in keywords)


def _truncate_reason(reason, limit=40):
    if not reason:
        return None
    trimmed = reason.strip()
    return trimmed[:limit] if trimmed else None

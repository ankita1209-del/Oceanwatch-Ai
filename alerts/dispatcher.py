"""
Alert Dispatcher
================
Sends HAB early-warning alerts via configured channels.

TODO (Member 3):
- Configure email settings in .env
- Add SMTP sending via smtplib or third-party SDK
- Add Slack/webhook support
"""

import os
from dataclasses import dataclass
from typing import Optional
from loguru import logger


@dataclass
class Alert:
    alert_id: str
    risk_level: str
    risk_score: float
    lat: float
    lon: float
    message: str
    notify_email: Optional[str] = None


def send_alert(alert: Alert) -> bool:
    """
    Dispatch an alert via all configured channels.

    Returns True if at least one channel succeeded.

    TODO: replace stub with real notification logic
    """
    logger.info(
        f"[ALERT {alert.alert_id}] Level={alert.risk_level} "
        f"Score={alert.risk_score:.1f} "
        f"Location=({alert.lat:.3f}, {alert.lon:.3f})"
    )
    logger.info(f"  Message: {alert.message}")

    # TODO: implement email, Slack, webhook dispatchers
    success = _log_to_file(alert)
    return success


def _log_to_file(alert: Alert) -> bool:
    """Persist alert to a local log file (development fallback)."""
    log_path = os.path.join("alerts", "alert_log.jsonl")
    try:
        import json
        from datetime import datetime
        record = {
            "alert_id": alert.alert_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "risk_level": alert.risk_level,
            "risk_score": alert.risk_score,
            "lat": alert.lat,
            "lon": alert.lon,
            "message": alert.message,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except Exception as e:
        logger.error(f"Failed to write alert log: {e}")
        return False

# backend/app/api/alerts.py
"""Anomaly detection and alerting."""

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.models.feedback import Feedback
from app.models.user import User
from app.services.auth_service import require_admin

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def get_alerts(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Check for anomalies and return active alerts."""
    alerts = []
    now = datetime.datetime.now(datetime.timezone.utc)
    recent_cutoff = now - datetime.timedelta(minutes=30)

    # Recent logs (last 30 min)
    recent_logs = (
        db.query(ConversationLog)
        .filter(ConversationLog.created_at >= recent_cutoff)
        .order_by(ConversationLog.created_at.desc())
        .limit(20)
        .all()
    )

    if not recent_logs:
        return {"alerts": [], "status": "ok"}

    # 1. High latency check
    recent_latencies = [log.latency_ms for log in recent_logs]
    avg_latency = sum(recent_latencies) / len(recent_latencies) if recent_latencies else 0
    if avg_latency > 10000:
        alerts.append({
            "level": "warning",
            "type": "high_latency",
            "message": f"最近30分钟平均延迟 {avg_latency:.0f}ms，超过阈值 10000ms",
            "value": round(avg_latency, 0),
            "threshold": 10000,
        })

    # 2. Empty result rate check
    empty_count = sum(1 for log in recent_logs if len(log.answer) <= 10)
    empty_rate = empty_count / len(recent_logs) if recent_logs else 0
    if empty_rate > 0.5:
        alerts.append({
            "level": "warning",
            "type": "high_empty_rate",
            "message": f"最近30分钟空结果率 {empty_rate:.0%}，超过阈值 50%",
            "value": round(empty_rate, 4),
            "threshold": 0.5,
        })

    # 3. Satisfaction check
    recent_feedbacks = (
        db.query(Feedback)
        .filter(Feedback.created_at >= recent_cutoff)
        .all()
    )
    if recent_feedbacks:
        likes = sum(1 for fb in recent_feedbacks if fb.rating == "like")
        satisfaction = likes / len(recent_feedbacks)
        if satisfaction < 0.3:
            alerts.append({
                "level": "critical",
                "type": "low_satisfaction",
                "message": f"最近30分钟满意度 {satisfaction:.0%}，低于阈值 30%",
                "value": round(satisfaction, 4),
                "threshold": 0.3,
            })

    return {
        "alerts": alerts,
        "status": "critical" if any(a["level"] == "critical" for a in alerts)
                  else "warning" if alerts
                  else "ok",
    }

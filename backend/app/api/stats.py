# backend/app/api/stats.py
"""Aggregated statistics for observability dashboard."""

import datetime
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation_log import ConversationLog
from app.models.feedback import Feedback

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get overall system statistics."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Total conversations
    total_conversations = db.query(ConversationLog).count()

    # Today's conversations
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(ConversationLog).filter(
        ConversationLog.created_at >= today_start
    ).count()

    # Average latency
    avg_latency = db.query(func.avg(ConversationLog.latency_ms)).scalar() or 0

    # P95 latency
    all_latencies = [
        r[0] for r in db.query(ConversationLog.latency_ms)
        .order_by(ConversationLog.latency_ms)
        .all()
    ]
    p95_latency = 0
    if all_latencies:
        idx = int(len(all_latencies) * 0.95)
        p95_latency = all_latencies[min(idx, len(all_latencies) - 1)]

    # Empty result rate (answers with very short content)
    total_with_content = db.query(ConversationLog).filter(
        func.length(ConversationLog.answer) > 10
    ).count()
    empty_result_rate = 0.0
    if total_conversations > 0:
        empty_count = total_conversations - total_with_content
        empty_result_rate = round(empty_count / total_conversations, 4)

    # Feedback stats
    total_feedback = db.query(Feedback).count()
    likes = db.query(Feedback).filter(Feedback.rating == "like").count()
    satisfaction = round(likes / total_feedback, 4) if total_feedback > 0 else 0.0

    return {
        "total_conversations": total_conversations,
        "today_conversations": today_count,
        "avg_latency_ms": round(avg_latency, 1),
        "p95_latency_ms": p95_latency,
        "empty_result_rate": empty_result_rate,
        "total_feedback": total_feedback,
        "satisfaction": satisfaction,
        "total_tokens": db.query(func.sum(ConversationLog.token_count)).scalar() or 0,
    }


@router.get("/trends")
def get_trends(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get daily trends for the last N days."""
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now - datetime.timedelta(days=days)

    logs = (
        db.query(ConversationLog)
        .filter(ConversationLog.created_at >= start)
        .order_by(ConversationLog.created_at)
        .all()
    )

    feedbacks = (
        db.query(Feedback)
        .filter(Feedback.created_at >= start)
        .order_by(Feedback.created_at)
        .all()
    )

    # Group by date
    daily_calls: dict[str, int] = defaultdict(int)
    daily_latency: dict[str, list[int]] = defaultdict(list)
    daily_empty: dict[str, int] = defaultdict(int)
    daily_likes: dict[str, int] = defaultdict(int)
    daily_dislikes: dict[str, int] = defaultdict(int)

    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d") if log.created_at else ""
        daily_calls[day] += 1
        daily_latency[day].append(log.latency_ms)
        if len(log.answer) <= 10:
            daily_empty[day] += 1

    for fb in feedbacks:
        day = fb.created_at.strftime("%Y-%m-%d") if fb.created_at else ""
        if fb.rating == "like":
            daily_likes[day] += 1
        elif fb.rating == "dislike":
            daily_dislikes[day] += 1

    # Fill in all days
    trends = []
    for i in range(days):
        day = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        latencies = daily_latency.get(day, [])
        total_calls = daily_calls.get(day, 0)
        total_likes = daily_likes.get(day, 0)
        total_dislikes = daily_dislikes.get(day, 0)
        total_fb = total_likes + total_dislikes

        trends.append({
            "date": day,
            "calls": total_calls,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "empty_results": daily_empty.get(day, 0),
            "likes": total_likes,
            "dislikes": total_dislikes,
            "satisfaction": round(total_likes / total_fb, 4) if total_fb > 0 else None,
        })

    return {"trends": trends, "days": days}

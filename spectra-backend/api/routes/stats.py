from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_current_user
from database.supabase_client import get_supabase_client
from utils.logging_config import setup_logging

logger = setup_logging("INFO", __name__)
router = APIRouter(prefix="/stats", tags=["stats"])


class StatsResponse(BaseModel):
    total_sessions: int
    avg_rating: Optional[float]
    current_streak: int
    longest_streak: int


def _calculate_streaks(session_dates: List[date]) -> tuple:
    if not session_dates:
        return 0, 0

    unique_dates = sorted(set(session_dates), reverse=True)
    today = datetime.now(timezone.utc).date()

    # Current streak: consecutive days ending today (or yesterday)
    current_streak = 0
    expected = today
    for d in unique_dates:
        if d == expected:
            current_streak += 1
            expected = date.fromordinal(expected.toordinal() - 1)
        elif d < expected:
            break

    # Longest streak: longest run of consecutive days
    longest = 1
    streak = 1
    asc = sorted(unique_dates)
    for i in range(1, len(asc)):
        if (asc[i].toordinal() - asc[i - 1].toordinal()) == 1:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 1

    return current_streak, longest


@router.get("", response_model=StatsResponse)
async def get_stats(current_user: dict = Depends(get_current_user)) -> StatsResponse:
    client = get_supabase_client()
    result = (
        client.table("sessions")
        .select("rating, start_time")
        .eq("user_id", current_user["id"])
        .execute()
    )

    sessions = result.data
    if not sessions:
        return StatsResponse(total_sessions=0, avg_rating=None, current_streak=0, longest_streak=0)

    total = len(sessions)
    avg_rating = round(sum(s["rating"] for s in sessions) / total, 2)

    session_dates: List[date] = []
    for s in sessions:
        try:
            dt = datetime.fromisoformat(s["start_time"].replace("Z", "+00:00"))
            session_dates.append(dt.date())
        except (ValueError, AttributeError):
            pass

    current_streak, longest_streak = _calculate_streaks(session_dates)
    return StatsResponse(
        total_sessions=total,
        avg_rating=avg_rating,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )

"""Teacher dashboard endpoint backed only by the logged-in Teacher's records."""

import sqlite3

from fastapi import APIRouter, Depends

from .auth_api import require_teacher
from .database import get_db
from .models import TeacherDashboardResponse
from .services.teacher_analytics_service import get_teacher_dashboard

router = APIRouter(tags=["teacher analytics"])


@router.get("/teacher/dashboard", response_model=TeacherDashboardResponse)
def teacher_dashboard(
    teacher: dict = Depends(require_teacher),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Aggregate the authenticated Teacher's own lecture records."""
    return get_teacher_dashboard(db, teacher_id=teacher["id"])

"""
API v1 package.
"""
from fastapi import APIRouter

from app.api.v1 import tasks, assignments, feedbacks, conflicts, memos, reminders, dashboard

api_router = APIRouter()

# Include all routers
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
api_router.include_router(feedbacks.router, prefix="/feedbacks", tags=["Feedbacks"])
api_router.include_router(conflicts.router, prefix="/conflicts", tags=["Conflicts"])
api_router.include_router(memos.router, prefix="/memos", tags=["Memos"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
api_router.include_router(dashboard.router, prefix="/leader", tags=["Leader Dashboard"])

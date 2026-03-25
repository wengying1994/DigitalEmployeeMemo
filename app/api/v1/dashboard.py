"""
Leader Dashboard API routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_leader_user
from app.db.session import get_db
from app.models import User
from app.schemas.memo import LeaderDashboard
from app.services.memo_service import MemoService


router = APIRouter()


def get_memo_service(db: AsyncSession = Depends(get_db)) -> MemoService:
    """Get memo service instance."""
    service = MemoService(db)
    service.db = db  # Ensure service has db reference
    return service


@router.get("/dashboard", response_model=LeaderDashboard)
async def get_leader_dashboard(
    current_user: User = Depends(get_leader_user),
    service: MemoService = Depends(get_memo_service)
) -> LeaderDashboard:
    """
    Get leader dashboard statistics.

    Returns:
    - Pending memos count
    - Unread memos count
    - Resolved today count
    - Pending conflicts count
    - Urgent conflicts count
    - Tasks in progress count
    - Tasks coordinating count
    - Tasks near deadline count
    - Recent memos (5)
    - Urgent conflicts (5)

    Only leaders can access this endpoint.
    """
    dashboard = await service.get_leader_dashboard(current_user)
    return dashboard

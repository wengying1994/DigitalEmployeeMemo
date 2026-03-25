"""
API dependencies for FastAPI dependency injection.
Provides authentication and database session management.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.db.session import get_db
from app.models import User


async def get_current_user(
    x_user_id: int = Header(..., description="User ID from auth header"),
    x_dept_id: int = Header(..., description="Department ID from auth header"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from headers.

    In production, this should be replaced with proper JWT authentication.
    For development, we use X-User-ID and X-Dept-ID headers.

    Args:
        x_user_id: User ID from header
        x_dept_id: Department ID from header
        db: Database session

    Returns:
        User instance

    Raises:
        UnauthorizedException: If user not found
    """
    result = await db.execute(
        select(User).where(
            User.id == x_user_id,
            User.is_deleted == False
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="User not found")

    # Update user's dept_id from header (in case they moved departments)
    if user.dept_id != x_dept_id:
        user.dept_id = x_dept_id
        await db.flush()

    return user


async def get_leader_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user and verify they are a leader.

    Args:
        current_user: Current authenticated user

    Returns:
        User instance (if leader)

    Raises:
        ForbiddenException: If user is not a leader
    """
    if current_user.role != "leader":
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException(message="Only leaders can perform this action")

    return current_user


class OptionalCurrentUser:
    """
    Optional current user dependency.
    Returns None if authentication headers are not provided.
    """

    async def __call__(
        self,
        x_user_id: Optional[int] = Header(None),
        x_dept_id: Optional[int] = Header(None),
        db: AsyncSession = Depends(get_db)
    ) -> Optional[User]:
        if x_user_id is None or x_dept_id is None:
            return None

        result = await db.execute(
            select(User).where(
                User.id == x_user_id,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()


# Pagination parameters dependency
def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> tuple[int, int]:
    """
    Get pagination parameters with validation.

    Args:
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Tuple of (page, page_size) with validation
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    return page, page_size

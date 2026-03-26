"""
API v1 package.
"""
from fastapi import APIRouter

from app.api.v1 import messages

api_router = APIRouter()

# Include all routers
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])

"""
Security utilities for authentication and authorization.
Note: This implementation uses header-based authentication for development.
In production, this should be replaced with JWT or OAuth2.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header, HTTPException, status

# Role definitions
class UserRole:
    """User role constants."""
    LEADER = "leader"           # 领导 - full access to all resources
    DEPT_HEAD = "dept_head"     # 部门负责人 - manage department tasks
    MEMBER = "member"           # 普通成员 - limited access


class Permission:
    """Permission constants for resource access."""

    # Task permissions
    CAN_CREATE_TASK = "can_create_task"
    CAN_UPDATE_TASK = "can_update_task"
    CAN_DELETE_TASK = "can_delete_task"
    CAN_VIEW_ALL_TASKS = "can_view_all_tasks"

    # Assignment permissions
    CAN_CREATE_ASSIGNMENT = "can_create_assignment"
    CAN_UPDATE_ASSIGNMENT = "can_update_assignment"
    CAN_VIEW_ASSIGNMENT = "can_view_assignment"

    # Feedback permissions
    CAN_SUBMIT_FEEDBACK = "can_submit_feedback"
    CAN_VIEW_FEEDBACK = "can_view_feedback"

    # Conflict permissions
    CAN_REPORT_CONFLICT = "can_report_conflict"
    CAN_VIEW_CONFLICT = "can_view_conflict"
    CAN_RESOLVE_CONFLICT = "can_resolve_conflict"

    # Memo permissions
    CAN_VIEW_MEMO = "can_view_memo"
    CAN_CREATE_MEMO = "can_create_memo"
    CAN_DECIDE_MEMO = "can_decide_memo"

    # Dashboard permissions
    CAN_VIEW_LEADER_DASHBOARD = "can_view_leader_dashboard"


# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.LEADER: [
        Permission.CAN_CREATE_TASK,
        Permission.CAN_UPDATE_TASK,
        Permission.CAN_DELETE_TASK,
        Permission.CAN_VIEW_ALL_TASKS,
        Permission.CAN_CREATE_ASSIGNMENT,
        Permission.CAN_UPDATE_ASSIGNMENT,
        Permission.CAN_VIEW_ASSIGNMENT,
        Permission.CAN_SUBMIT_FEEDBACK,
        Permission.CAN_VIEW_FEEDBACK,
        Permission.CAN_REPORT_CONFLICT,
        Permission.CAN_VIEW_CONFLICT,
        Permission.CAN_RESOLVE_CONFLICT,
        Permission.CAN_VIEW_MEMO,
        Permission.CAN_CREATE_MEMO,
        Permission.CAN_DECIDE_MEMO,
        Permission.CAN_VIEW_LEADER_DASHBOARD,
    ],
    UserRole.DEPT_HEAD: [
        Permission.CAN_VIEW_ALL_TASKS,  # Can view tasks their department is involved in
        Permission.CAN_CREATE_ASSIGNMENT,
        Permission.CAN_UPDATE_ASSIGNMENT,
        Permission.CAN_VIEW_ASSIGNMENT,
        Permission.CAN_SUBMIT_FEEDBACK,
        Permission.CAN_VIEW_FEEDBACK,
        Permission.CAN_REPORT_CONFLICT,
        Permission.CAN_VIEW_CONFLICT,
        Permission.CAN_VIEW_MEMO,
    ],
    UserRole.MEMBER: [
        Permission.CAN_VIEW_ASSIGNMENT,
        Permission.CAN_SUBMIT_FEEDBACK,
        Permission.CAN_VIEW_FEEDBACK,
        Permission.CAN_VIEW_MEMO,
    ],
}


def check_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: The user's role
        permission: The permission to check

    Returns:
        True if the role has the permission, False otherwise
    """
    return permission in ROLE_PERMISSIONS.get(role, [])


def generate_mock_token(user_id: int, dept_id: int, role: str) -> str:
    """
    Generate a mock token for development/testing.
    In production, use proper JWT tokens.

    Args:
        user_id: User ID
        dept_id: Department ID
        role: User role

    Returns:
        Mock token string
    """
    # This is a simplified mock - in production use JWT
    import base64
    import json
    payload = json.dumps({"user_id": user_id, "dept_id": dept_id, "role": role})
    return base64.b64encode(payload.encode()).decode()


def decode_mock_token(token: str) -> Optional[dict]:
    """
    Decode a mock token for development/testing.

    Args:
        token: The mock token string

    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        import base64
        payload = base64.b64decode(token.encode()).decode()
        return json.loads(payload)
    except Exception:
        return None

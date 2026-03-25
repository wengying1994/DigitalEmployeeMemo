"""
Custom exceptions for the DigitalEmployeeMemo application.
All exceptions follow a consistent format with error codes.
"""
from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception for all application exceptions."""

    # Error code ranges:
    # 1001-1999: Authentication/Authorization errors
    # 2001-2999: Resource not found errors
    # 3001-3999: Validation/Parameter errors
    # 4001-4999: Business logic errors
    # 5001-5999: Internal server errors

    error_code: int = 5001
    message: str = "An internal error occurred"
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details
        }


# Authentication/Authorization Errors (1001-1999)
class UnauthorizedException(BaseAppException):
    """User is not authenticated."""
    error_code = 1001
    message = "Authentication required"
    status_code = 401


class ForbiddenException(BaseAppException):
    """User does not have permission to perform this action."""
    error_code = 1002
    message = "Permission denied"
    status_code = 403


# Resource Not Found Errors (2001-2999)
class ResourceNotFoundException(BaseAppException):
    """The requested resource does not exist."""
    error_code = 2001
    message = "Resource not found"
    status_code = 404

    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class TaskNotFoundException(ResourceNotFoundException):
    """Task not found."""
    def __init__(self, task_id: int):
        super().__init__("Task", task_id)


class AssignmentNotFoundException(ResourceNotFoundException):
    """Assignment not found."""
    def __init__(self, assignment_id: int):
        super().__init__("Assignment", assignment_id)


class FeedbackNotFoundException(ResourceNotFoundException):
    """Feedback not found."""
    def __init__(self, feedback_id: int):
        super().__init__("Feedback", feedback_id)


class ConflictNotFoundException(ResourceNotFoundException):
    """Conflict report not found."""
    def __init__(self, conflict_id: int):
        super().__init__("ConflictReport", conflict_id)


class MemoNotFoundException(ResourceNotFoundException):
    """Memo not found."""
    def __init__(self, memo_id: int):
        super().__init__("Memo", memo_id)


class UserNotFoundException(ResourceNotFoundException):
    """User not found."""
    def __init__(self, user_id: int):
        super().__init__("User", user_id)


class DepartmentNotFoundException(ResourceNotFoundException):
    """Department not found."""
    def __init__(self, dept_id: int):
        super().__init__("Department", dept_id)


# Validation/Parameter Errors (3001-3999)
class ValidationException(BaseAppException):
    """Input validation failed."""
    error_code = 3001
    message = "Validation error"
    status_code = 400

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message=message, details=details)


class InvalidParameterException(ValidationException):
    """Invalid parameter value."""
    error_code = 3002
    message = "Invalid parameter"
    status_code = 400


# Business Logic Errors (4001-4999)
class BusinessLogicException(BaseAppException):
    """Business logic rule violation."""
    error_code = 4001
    message = "Operation not allowed"
    status_code = 400


class TaskStatusException(BusinessLogicException):
    """Cannot perform operation due to task status."""
    error_code = 4002
    message = "Operation not allowed for current task status"

    def __init__(self, current_status: str, required_status: str):
        super().__init__(
            message=f"Task status is '{current_status}', expected '{required_status}'",
            details={"current_status": current_status, "required_status": required_status}
        )


class ConflictAlreadyResolvedException(BusinessLogicException):
    """Conflict has already been resolved."""
    error_code = 4003
    message = "Conflict has already been resolved"
    status_code = 400


class DuplicateResourceException(BusinessLogicException):
    """Resource already exists."""
    error_code = 4004
    message = "Resource already exists"

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} '{identifier}' already exists",
            details={"resource_type": resource_type, "identifier": identifier}
        )


class DeadlinePassedException(BusinessLogicException):
    """Deadline has passed."""
    error_code = 4005
    message = "Deadline has passed"
    status_code = 400


class NotLeadDepartmentException(BusinessLogicException):
    """Only the lead department can perform this action."""
    error_code = 4006
    message = "Only the lead department can perform this action"


class DependencyNotMetException(BusinessLogicException):
    """Task dependency not met."""
    error_code = 4007
    message = "Task dependency not met"

    def __init__(self, dependency_task_id: int):
        super().__init__(
            message=f"Dependency task {dependency_task_id} is not completed",
            details={"dependency_task_id": dependency_task_id}
        )


# Internal Server Errors (5001-5999)
class DatabaseException(BaseAppException):
    """Database operation failed."""
    error_code = 5001
    message = "Database operation failed"
    status_code = 500


class ExternalServiceException(BaseAppException):
    """External service call failed."""
    error_code = 5002
    message = "External service unavailable"
    status_code = 503


class CacheException(BaseAppException):
    """Cache operation failed."""
    error_code = 5003
    message = "Cache operation failed"
    status_code = 500

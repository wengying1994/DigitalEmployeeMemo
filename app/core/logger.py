"""
Logging configuration for the application.
Provides structured logging with contextual information.
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger


class AppJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with application-specific fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add source location
        log_record["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }

        # Move message to proper field if not already there
        if "message" not in log_record:
            log_record["message"] = record.getMessage()


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Set format based on environment
    if sys.stderr.isatty():
        # Terminal - use colored text format
        format_str = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")
    else:
        # Docker/production - use JSON format
        formatter = AppJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )

    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__ of the module

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to provide logging capability to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


# Operation log types
class OperationType:
    """Enum-like class for operation types in audit log."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    LOGIN = "login"
    LOGOUT = "logout"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    NOTIFY = "notify"


class AuditLog:
    """
    Audit logger for tracking user operations.
    Writes to a dedicated audit logger that can be shipped to a separate store.
    """

    def __init__(self):
        self._logger = logging.getLogger("audit")
        # Ensure audit logger has a handler
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter := logging.Formatter(
                "%(asctime)s | AUDIT | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            self._logger.addHandler(handler)
            self._logger.propagate = False

    def log(
        self,
        operation: str,
        user_id: int,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        dept_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log an operation.

        Args:
            operation: Type of operation (see OperationType)
            user_id: ID of user performing the operation
            resource_type: Type of resource being operated on
            resource_id: ID of the resource (if applicable)
            details: Additional operation details
            dept_id: Department ID of the user
            ip_address: Client IP address
        """
        log_data = {
            "operation": operation,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
        }
        if dept_id:
            log_data["dept_id"] = dept_id
        if ip_address:
            log_data["ip_address"] = ip_address

        self._logger.info(str(log_data))


# Global audit log instance
audit_log = AuditLog()

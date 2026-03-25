"""
DigitalEmployeeMemo FastAPI Application Entry Point.

This is the main application file that:
- Creates the FastAPI application
- Configures CORS and middleware
- Registers all routers
- Sets up exception handlers
- Handles startup/shutdown events
"""
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import BaseAppException
from app.core.logger import setup_logging, get_logger
from app.db.session import init_db, close_db
from app.api.v1 import api_router


# Setup logging
setup_logging(level="DEBUG" if settings.DEBUG else "INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting DigitalEmployeeMemo API...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down DigitalEmployeeMemo API...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="DigitalEmployeeMemo API",
    description="""
    DigitalEmployeeMemo - 企业内部跨部门协作任务管理系统

    ## 功能

    * 任务管理 - 领导创建任务，指定牵头部门
    * 分工登记 - 牵头部门为任务登记各协办部门的分工
    * 部门反馈 - 协办部门对分工提出反馈
    * 冲突上报 - 协调过程中的冲突上报
    * 领导备忘录 - 领导查看并处理冲突报告
    * 智能提醒 - 多阶段提醒和升级机制

    ## 认证

    使用 Header 进行身份验证：
    * X-User-ID: 用户ID
    * X-Dept-ID: 部门ID
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(BaseAppException)
async def app_exception_handler(
    request: Request,
    exc: BaseAppException
) -> JSONResponse:
    """
    Handle application-specific exceptions.
    """
    logger.warning(
        f"Application exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 3001,
            "message": "Validation error",
            "details": {"errors": errors}
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 5001,
            "message": "An internal error occurred",
            "details": {}
        }
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns the service status.
    """
    return {
        "status": "healthy",
        "service": "DigitalEmployeeMemo API",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    Returns basic service information.
    """
    return {
        "service": "DigitalEmployeeMemo API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )

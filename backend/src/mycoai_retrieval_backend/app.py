from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.router import router as api_router
from .config import get_settings
from .core.exceptions import AppError
from .core.middleware import RequestIDMiddleware, RequestLoggingMiddleware
from .routers.search import router as search_router
from .routes import create_image_router
from .schemas import ProblemDetails
from .segmentation import ImageStore, SegmentationPipeline


def create_app() -> FastAPI:
    settings = get_settings()

    upload_root = settings.upload_root
    upload_root.mkdir(parents=True, exist_ok=True)

    store = ImageStore(upload_root)
    pipeline = SegmentationPipeline(upload_root)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/static", StaticFiles(directory=str(upload_root)), name="static")
    app.include_router(create_image_router(store=store, pipeline=pipeline))
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(search_router)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        body = ProblemDetails(
            type=exc.error_type,
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            instance=str(request.url.path),
            errors=getattr(exc, "errors", None),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(exclude_none=True),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        title = "Not Found" if exc.status_code == 404 else str(exc.detail)
        body = ProblemDetails(
            type="https://api.mycoai.dev/errors/http",
            title=title,
            status=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(exclude_none=True),
        )

    @app.get("/health", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.environment,
        }

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()

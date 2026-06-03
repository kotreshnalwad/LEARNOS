from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import get_settings
from app.db.database import init_db, dispose_db
from app.api.routes.roadmaps import router as roadmaps_router
from app.api.routes.learning import progress_router, quiz_router, tutor_router
from app.api.routes.users import users_router, topics_router, recommendations_router, webhook_router

settings = get_settings()
logger = structlog.get_logger()

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LearnOS API starting", version=settings.APP_VERSION)
    await init_db()
    yield
    await dispose_db()
    logger.info("LearnOS API stopped")

app = FastAPI(
    title="LearnOS AI API",
    version=settings.APP_VERSION,
    description="AI-powered learning operating system",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    from app.core.cache import get_redis
    client_ip = request.client.host if request.client else "unknown"
    key = f"rl:{client_ip}"
    try:
        r = await get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, settings.RATE_LIMIT_WINDOW)
        if count > settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    except Exception:
        pass
    return await call_next(request)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    import time
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    logger.info("req", method=request.method, path=request.url.path, status=response.status_code, ms=ms)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.include_router(roadmaps_router)
app.include_router(progress_router)
app.include_router(quiz_router)
app.include_router(tutor_router)
app.include_router(users_router)
app.include_router(topics_router)
app.include_router(recommendations_router)
app.include_router(webhook_router)

@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION, "environment": settings.ENVIRONMENT}

@app.get("/")
async def root():
    return {"name": "LearnOS AI API", "version": settings.APP_VERSION}

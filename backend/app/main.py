from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.routes import router
from app.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    cors_origins,
    debug_enabled,
    trusted_hosts,
)

_debug = debug_enabled()
app = FastAPI(
    title="PremierIQ",
    version="1.0.0",
    docs_url="/docs" if _debug else None,
    redoc_url="/redoc" if _debug else None,
    openapi_url="/openapi.json" if _debug else None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, max_hits=90, window_s=60)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts())
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=False,
)
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"name": "PremierIQ", "status": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}

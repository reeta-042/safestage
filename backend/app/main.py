from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.connection import engine, Base
from app.api.routes import events, analyze, heatmap, simulate, chat, report

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SafeStage AI Climate Operations Backend powered by FortyGuard Hyperlocal Temperature Intelligence.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(events.router)
app.include_router(analyze.router)
app.include_router(heatmap.router)
app.include_router(simulate.router)
app.include_router(chat.router)
app.include_router(report.router)

@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint returning system status and current climate provider mode.
    """
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "climate_provider": settings.CLIMATE_PROVIDER,
        "fortyguard_base_url": settings.FORTYGUARD_BASE_URL,
        "fortyguard_key_configured": bool(settings.FORTYGUARD_API_KEY)
    }

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.routes import router
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
from app.models.database import init_db
init_db()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

app.include_router(router)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started on {settings.HOST}:{settings.PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
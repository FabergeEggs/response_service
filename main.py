import logging
from fastapi import FastAPI
import uvicorn
from src.api.handlers import router
from src.core.config import settings
from src.core.lifespan import lifespan

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Response Service",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/response", tags=["responses"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
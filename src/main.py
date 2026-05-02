from fastapi import FastAPI
from src.api.handlers import router
from src.core.config import settings
from src.core.lifespan import lifespan

app = FastAPI(
    title="Response Service",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )

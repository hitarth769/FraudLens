from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.models import Health
from app.api import cases, investigate, metrics

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(investigate.router, prefix="/api", tags=["investigation"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])

@app.get("/api/health", response_model=Health)
async def get_health():
    return Health(
        status="ok",
        mode=settings.MODE,
        llm="unavailable",
        version="0.1.0"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

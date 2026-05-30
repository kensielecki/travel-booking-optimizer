from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.demo import router as demo_router
from app.api.ingestion import router as ingestion_router
from app.api.optimize import router as optimize_router
from app.api.shopping import router as shopping_router
from app.api.travel_search import router as travel_search_router

app = FastAPI(
    title="Travel Booking Optimizer API",
    description="Deterministic travel and loyalty payment-path optimization.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demo_router)
app.include_router(ingestion_router)
app.include_router(optimize_router)
app.include_router(shopping_router)
app.include_router(travel_search_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

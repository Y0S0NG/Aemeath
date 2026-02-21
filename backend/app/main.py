from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.guidance_routes import router as guidance_router
from app.api.plan_routes import router as plan_router

app = FastAPI(title="theGuider API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plan_router)
app.include_router(guidance_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

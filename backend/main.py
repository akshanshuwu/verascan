from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import face, search, hash

load_dotenv()

app = FastAPI(
    title="VeraScan API",
    description="Face identification and blockchain verification pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(face.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(hash.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

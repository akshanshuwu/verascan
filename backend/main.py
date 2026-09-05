from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import os

from routers import face, search, hash

load_dotenv()


def _cors_origins() -> list:
    """Allowed frontend origins. Comma-separated CORS_ORIGINS wins,
    else FRONTEND_URL, else local dev defaults (no code change to deploy)."""
    raw = os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_URL") or ""
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    if not origins:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    return origins

app = FastAPI(
    title="VeraScan API",
    description="Face identification and blockchain verification pipeline",
    version="1.0.0",
)

_CORS_ORIGINS = _cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials="*" not in _CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(face.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(hash.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# CLI entry point (backend showcase). Only triggers when main.py is executed
# directly with a CLI subcommand: `python main.py scan ...` /
# `python main.py verify ...`. `uvicorn main:app ...` imports this module
# without those argv values, so the FastAPI app is unaffected.
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("scan", "verify", "-h", "--help"):
        from cli import main as cli_main

        raise SystemExit(cli_main())
    print("VeraScan API. Run the server with: uvicorn main:app --host 127.0.0.1 --port 8000")
    print("Or use the backend CLI: python main.py --help")

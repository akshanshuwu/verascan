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

import os
import sys
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Add backend root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app
except Exception as e:
    err_tb = traceback.format_exc()
    app = FastAPI(title="ABYSS API Diagnostic Fallback")

    @app.get("/")
    @app.get("/{full_path:path}")
    @app.post("/{full_path:path}")
    async def catch_all(full_path: str = ""):
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "traceback": err_tb.splitlines()[-10:],
                "message": "Backend initialization exception caught on Vercel Serverless Function"
            }
        )

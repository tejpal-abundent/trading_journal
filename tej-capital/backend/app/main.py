from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import NotConfiguredError
from app.api.health import router as health_router


app = FastAPI(title="TEJ Capital API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.exception_handler(NotConfiguredError)
async def _not_configured(_request: Request, exc: NotConfiguredError):
    return JSONResponse(
        status_code=501,
        content={
            "error": "not_configured",
            "integration": exc.integration,
            "hint": exc.hint,
        },
    )

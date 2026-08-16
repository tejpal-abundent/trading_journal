from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.accounts import router as accounts_router
from app.api.errors import NotConfiguredError
from app.api.flows import router as flows_router
from app.api.health import router as health_router
from app.api.nav import router as nav_router
from app.api.playbook import router as playbook_router
from app.api.settings import router as settings_router
from app.api.trades import router as trades_router


app = FastAPI(title="TEJ Capital API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(accounts_router)
app.include_router(settings_router)
app.include_router(playbook_router)
app.include_router(nav_router)
app.include_router(flows_router)
app.include_router(trades_router)


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

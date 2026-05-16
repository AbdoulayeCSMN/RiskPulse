"""
RiskPulse FastAPI Server.

Demarrage : `python -m api.server` ou via la vue API & SDK dans l'app.
Tourne dans un thread separe pour ne pas bloquer Qt.
"""

import logging
import threading
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from api import __version__
from api.routes import health, analyze, knowledge, monitoring, predictive
from api.deps import set_controller

logger = logging.getLogger("riskpulse.api")


# ─────────────────────────────────────────────
#  FACTORY
# ─────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="RiskPulse API",
        version=__version__,
        description=(
            "REST API exposing the RiskPulse risk intelligence engine. "
            "Authenticated via the `X-API-Key` header for protected routes."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS permissif en local — restreindre en prod
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes versionnees
    PREFIX = "/v1"
    app.include_router(health.router,      prefix=PREFIX)
    app.include_router(analyze.router,     prefix=PREFIX)
    app.include_router(knowledge.router,   prefix=PREFIX)
    app.include_router(monitoring.router,  prefix=PREFIX)
    app.include_router(predictive.router,  prefix=PREFIX)

    @app.get("/")
    def root():
        return RedirectResponse("/docs")

    @app.exception_handler(Exception)
    async def all_exceptions(request, exc):
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal error: {exc}"},
        )

    return app


# ─────────────────────────────────────────────
#  SERVER MANAGER (thread-based, Qt-safe)
# ─────────────────────────────────────────────

class APIServer:
    """
    Wrapper qui demarre/arrete un uvicorn dans un thread, sans bloquer Qt.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                  controller=None):
        self.host = host
        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._server: Optional[uvicorn.Server] = None
        self._lock = threading.Lock()
        if controller is not None:
            set_controller(controller)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._server.started

    def start(self):
        with self._lock:
            if self._server is not None:
                logger.warning("API server already running")
                return
            # Licence : REST API necessite ENTERPRISE (ou trial)
            try:
                from services.licensing import get_license_manager
                if not get_license_manager().can_use("rest_api"):
                    raise PermissionError(
                        "REST API requires an ENTERPRISE license. "
                        "Activate one via Ctrl+L in the app."
                    )
            except PermissionError:
                raise
            except Exception as exc:
                logger.warning("Licensing check failed, allowing start: %s", exc)
            app = create_app()
            config = uvicorn.Config(
                app, host=self.host, port=self.port,
                log_level="warning",
                access_log=False,
                # Important : pas de reload, pas de signals (on est dans un thread)
                use_colors=False,
            )
            self._server = uvicorn.Server(config)
            # uvicorn par defaut s'enregistre comme signal handler -> casse Qt
            # On override ca :
            self._server.install_signal_handlers = lambda: None  # type: ignore
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="riskpulse-api"
            )
            self._thread.start()
            logger.info(f"API server starting on {self.url}")

    def _run(self):
        try:
            self._server.run()
        except Exception:
            logger.exception("uvicorn loop crashed")
        finally:
            self._server = None
            self._thread = None

    def stop(self, timeout: float = 5.0):
        with self._lock:
            if self._server is None:
                return
            self._server.should_exit = True
        # Attente courte
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        self._server = None
        self._thread = None
        logger.info("API server stopped")


# ─────────────────────────────────────────────
#  Singleton ergonomique
# ─────────────────────────────────────────────

_server_instance: Optional[APIServer] = None


def get_server(controller=None, host="127.0.0.1", port=8765) -> APIServer:
    global _server_instance
    if _server_instance is None:
        _server_instance = APIServer(host=host, port=port, controller=controller)
    elif controller is not None:
        set_controller(controller)
    return _server_instance


# ─────────────────────────────────────────────
#  CLI : python -m api.server
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from controller.risk_controller import RiskController
    ctrl = RiskController(language="fr")
    set_controller(ctrl)

    app = create_app()
    from api.auth import get_or_create_api_key
    print(f"\nRiskPulse API key : {get_or_create_api_key()}\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")

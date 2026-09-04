from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.app.api.router import router

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        f"Starting {settings.app_name} with backend={settings.engine_backend} "
        f"(demo_enabled={settings.enable_demo})"
    )
    if settings.engine_backend in ("ocr_hybrid", "visual_model", "local_cpu") and settings.ollama_preload:
        from src.app.api.deps import get_engine_singleton
        engine = get_engine_singleton()
        try:
            await engine.warmup()
        except Exception as err:
            logger.warning(f"Engine startup warmup notice: {err}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="FastAPI service for converting images and documents to structured JSON.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routes
    app.include_router(router)

    # Mount Interactive Demo UI & Trace folder if ENABLE_DEMO is true
    if settings.enable_demo:
        demo_html_path = Path(__file__).parent / "static" / "demo.html"
        trace_path = Path(settings.trace_dir)
        trace_path.mkdir(parents=True, exist_ok=True)

        from fastapi.staticfiles import StaticFiles
        app.mount("/trace", StaticFiles(directory=str(trace_path)), name="trace")

        @app.get("/demo", response_class=HTMLResponse, tags=["Demo"], include_in_schema=True)
        @app.get("/", response_class=HTMLResponse, tags=["Demo"], include_in_schema=False)
        async def serve_demo():
            if demo_html_path.exists():
                return HTMLResponse(content=demo_html_path.read_text(encoding="utf-8"))
            return HTMLResponse(content="<h1>Demo UI file not found</h1>", status_code=404)

    return app


app = create_app()

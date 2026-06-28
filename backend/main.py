from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import agent, analysis, experiments, health, samples
from backend.core.config import ROOT_DIR, get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.session_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="SIREN Experiment API",
        version="2.0.0",
        description="SIREN/PINN diffraction analysis and RAG experiment agent",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.siren_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(experiments.router, prefix="/api")
    application.include_router(agent.router, prefix="/api")
    application.include_router(analysis.router, prefix="/api")
    application.include_router(samples.router, prefix="/api")
    application.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
    application.mount("/output", StaticFiles(directory=settings.output_dir), name="output")
    sample_dir = ROOT_DIR / "static" / "samples"
    if sample_dir.exists():
        application.mount("/samples", StaticFiles(directory=sample_dir), name="sample-files")
    frontend_dist = ROOT_DIR / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    # Register the mount even when the frontend has not been built yet.  The
    # dist directory may be created after the API starts during development;
    # skipping the mount in that case makes asset requests fall through to the
    # SPA route and return index.html as JavaScript/CSS.
    application.mount(
        "/assets",
        StaticFiles(directory=assets_dir, check_dir=False),
        name="frontend-assets",
    )

    @application.get("/{path:path}", include_in_schema=False)
    async def vue_spa(path: str):
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=503, detail="前端尚未构建，请运行 npm run build")

    @application.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"success": False, "message": "请求参数无效", "errors": exc.errors()})

    @application.exception_handler(ValueError)
    async def value_error(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"success": False, "message": str(exc)})

    return application


app = create_app()

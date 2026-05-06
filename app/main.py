from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import Base, engine
from app.routes import companies, landing, phases
from app.utils import fmt_money, fmt_num, fmt_pct, parse_metrics

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Idempotent — không drop, chỉ create nếu thiếu.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["num"] = fmt_num
templates.env.filters["pct"] = fmt_pct
templates.env.filters["money"] = fmt_money
templates.env.filters["metrics"] = parse_metrics


def render(request: Request, tpl: str, **ctx) -> HTMLResponse:
    ctx.setdefault("settings", settings)
    return templates.TemplateResponse(request, tpl, ctx)


app.state.render = render

app.include_router(landing.router)
app.include_router(companies.router)
app.include_router(phases.router)

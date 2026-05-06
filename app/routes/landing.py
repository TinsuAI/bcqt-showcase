from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company

router = APIRouter()


@router.get("/")
def landing(request: Request, db: Session = Depends(get_db)):
    companies = db.scalars(select(Company).order_by(Company.created_at.desc())).all()
    stats = {
        "total_companies": db.scalar(select(func.count()).select_from(Company)) or 0,
        "phases": 6,
        "regulations": 6,  # TT 38, TT 39, TT 121, QĐ 1357, CV 3304, ...
    }
    return request.app.state.render(request, "landing.html", companies=companies, stats=stats)

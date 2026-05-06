from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company, ProcessLog, RiskFinding

router = APIRouter()


@router.get("/")
def landing(request: Request, db: Session = Depends(get_db)):
    companies = db.scalars(select(Company).order_by(Company.created_at.desc())).all()

    main = db.scalar(select(Company).where(Company.slug == "fdi-a-bn"))
    recent_logs = []
    top_risks = []
    if main:
        recent_logs = db.scalars(
            select(ProcessLog)
            .where(ProcessLog.company_id == main.id)
            .order_by(desc(ProcessLog.occurred_on), desc(ProcessLog.id))
            .limit(8)
        ).all()
        top_risks = db.scalars(
            select(RiskFinding)
            .where(RiskFinding.company_id == main.id, RiskFinding.severity == "high")
            .order_by(RiskFinding.code)
            .limit(4)
        ).all()

    stats = {
        "total_companies": db.scalar(select(func.count()).select_from(Company)) or 0,
        "phases": 6,
        "regulations": 6,
    }
    return request.app.state.render(
        request, "landing.html",
        companies=companies, stats=stats,
        recent_logs=recent_logs, top_risks=top_risks, main=main,
    )

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company, PhaseRun

router = APIRouter(prefix="/c", tags=["companies"])


def get_company_or_404(db: Session, slug: str) -> Company:
    c = db.scalar(select(Company).where(Company.slug == slug))
    if not c:
        raise HTTPException(404, f"Company not found: {slug}")
    return c


@router.get("/{slug}")
def company_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    c = get_company_or_404(db, slug)
    runs = db.scalars(
        select(PhaseRun).where(PhaseRun.company_id == c.id).order_by(PhaseRun.phase_no)
    ).all()
    return request.app.state.render(request, "company.html", company=c, phase_runs=runs)

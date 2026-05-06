"""Trang truy vết NVL + phát hiện rủi ro + nhật ký xử lý."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Mau16Row, NvlTraceability, ProcessLog, RiskFinding
from app.routes.companies import get_company_or_404

router = APIRouter(prefix="/c/{slug}", tags=["insights"])


@router.get("/trace")
def trace(slug: str, request: Request, db: Session = Depends(get_db),
          q: str | None = Query(None)):
    c = get_company_or_404(db, slug)

    summary = db.execute(
        select(
            func.count(),
            func.sum(NvlTraceability.xuat_sx),
            func.sum(NvlTraceability.giai_trinh),
            func.sum(NvlTraceability.con_lai),
        ).where(NvlTraceability.company_id == c.id)
    ).one()
    n_total, total_xuat, total_giai, total_con = summary
    pct_overall = (total_giai / total_xuat * 100) if total_xuat else 0

    suggestions = db.scalars(
        select(NvlTraceability)
        .where(NvlTraceability.company_id == c.id)
        .order_by(desc(NvlTraceability.xuat_sx))
        .limit(8)
    ).all()

    selected = None
    consumed_by = []
    if q:
        selected = db.scalar(
            select(NvlTraceability).where(
                NvlTraceability.company_id == c.id,
                NvlTraceability.material == q,
            )
        )
        if selected:
            consumed_by = db.scalars(
                select(Mau16Row)
                .where(Mau16Row.company_id == c.id, Mau16Row.nvl_code == q)
                .order_by(desc(Mau16Row.norm))
                .limit(20)
            ).all()

    return request.app.state.render(
        request, "insights/trace.html",
        company=c, q=q or "",
        n_total=n_total or 0,
        total_xuat=float(total_xuat or 0),
        total_giai=float(total_giai or 0),
        total_con=float(total_con or 0),
        pct_overall=pct_overall,
        suggestions=suggestions,
        selected=selected,
        consumed_by=consumed_by,
    )


@router.get("/risks")
def risks(slug: str, request: Request, db: Session = Depends(get_db)):
    c = get_company_or_404(db, slug)

    items = db.scalars(
        select(RiskFinding)
        .where(RiskFinding.company_id == c.id)
        .order_by(
            # high → medium → low
            (RiskFinding.severity == "high").desc(),
            (RiskFinding.severity == "medium").desc(),
            RiskFinding.code,
        )
    ).all()

    counts = {"high": 0, "medium": 0, "low": 0}
    for r in items:
        counts[r.severity] = counts.get(r.severity, 0) + 1

    return request.app.state.render(
        request, "insights/risks.html",
        company=c, risks=items, counts=counts,
    )


@router.get("/log")
def process_log(slug: str, request: Request, db: Session = Depends(get_db),
                phase: int | None = Query(None)):
    c = get_company_or_404(db, slug)

    stmt = select(ProcessLog).where(ProcessLog.company_id == c.id)
    if phase is not None:
        stmt = stmt.where(ProcessLog.phase_no == phase)
    logs = db.scalars(stmt.order_by(desc(ProcessLog.occurred_on), desc(ProcessLog.id))).all()

    return request.app.state.render(
        request, "insights/log.html",
        company=c, logs=logs, selected_phase=phase,
    )

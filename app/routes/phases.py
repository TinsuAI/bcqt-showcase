"""6 phase landing pages."""

from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AuditFinding,
    BcctRecord,
    BomCycle,
    BomCycleEdge,
    Company,
    Investigation,
    Material,
    Mau15Row,
    Mau15aRow,
    Mau16Row,
    Mb51Movement,
    PhaseRun,
    RawFile,
    ValidationResult,
)
from app.routes.companies import get_company_or_404

router = APIRouter(prefix="/c/{slug}/phase", tags=["phases"])


def _ctx(db: Session, slug: str) -> tuple[Company, PhaseRun | None]:
    c = get_company_or_404(db, slug)
    return c, None


@router.get("/1")
def phase1(slug: str, request: Request, db: Session = Depends(get_db)):
    c, _ = _ctx(db, slug)
    raw = db.scalars(select(RawFile).where(RawFile.company_id == c.id)).all()
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 1))
    sample_mb51 = db.scalars(
        select(Mb51Movement).where(Mb51Movement.company_id == c.id).limit(20)
    ).all()
    sample_bcct = db.scalars(
        select(BcctRecord).where(BcctRecord.company_id == c.id).limit(20)
    ).all()
    return request.app.state.render(
        request, "phases/phase1.html",
        company=c, run=run, raw_files=raw,
        sample_mb51=sample_mb51, sample_bcct=sample_bcct,
    )


@router.get("/2")
def phase2(slug: str, request: Request, db: Session = Depends(get_db)):
    c, _ = _ctx(db, slug)
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 2))

    cat_rows = db.execute(
        select(Material.category, func.count())
        .where(Material.company_id == c.id, Material.category.is_not(None))
        .group_by(Material.category)
        .order_by(desc(func.count()))
    ).all()
    by_category = [{"category": cat, "count": n} for cat, n in cat_rows]

    type_rows = db.execute(
        select(Material.material_type, func.count())
        .where(Material.company_id == c.id, Material.material_type.is_not(None))
        .group_by(Material.material_type)
        .order_by(desc(func.count()))
    ).all()
    by_type = [{"type": t, "count": n} for t, n in type_rows]

    conflicts = db.scalar(
        select(func.count()).select_from(Material).where(
            Material.company_id == c.id, Material.has_conflict.is_(True)
        )
    ) or 0
    sample_conflicts = db.scalars(
        select(Material).where(
            Material.company_id == c.id, Material.has_conflict.is_(True)
        ).limit(20)
    ).all()
    return request.app.state.render(
        request, "phases/phase2.html",
        company=c, run=run,
        by_category=by_category, by_type=by_type,
        conflicts_count=conflicts, sample_conflicts=sample_conflicts,
    )


@router.get("/3")
def phase3(slug: str, request: Request, db: Session = Depends(get_db),
           test: str | None = Query(None)):
    c, _ = _ctx(db, slug)
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 3))

    by_test = db.execute(
        select(AuditFinding.test_code, AuditFinding.test_name, func.count(), AuditFinding.severity)
        .where(AuditFinding.company_id == c.id)
        .group_by(AuditFinding.test_code, AuditFinding.test_name, AuditFinding.severity)
        .order_by(AuditFinding.test_code)
    ).all()

    grouped: dict = defaultdict(lambda: {"name": "", "count": 0, "critical": 0, "warning": 0, "info": 0})
    for code, name, n, sev in by_test:
        grouped[code]["name"] = name
        grouped[code]["count"] += n
        grouped[code][sev] = grouped[code].get(sev, 0) + n
    summary = [{"code": k, **v} for k, v in sorted(grouped.items())]

    findings = []
    if test:
        findings = db.scalars(
            select(AuditFinding)
            .where(AuditFinding.company_id == c.id, AuditFinding.test_code == test)
            .limit(50)
        ).all()
    return request.app.state.render(
        request, "phases/phase3.html",
        company=c, run=run, summary=summary, selected_test=test, findings=findings,
    )


@router.get("/4")
def phase4(slug: str, request: Request, db: Session = Depends(get_db)):
    c, _ = _ctx(db, slug)
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 4))
    invs = db.scalars(
        select(Investigation).where(Investigation.company_id == c.id).order_by(Investigation.inv_code)
    ).all()
    return request.app.state.render(
        request, "phases/phase4.html",
        company=c, run=run, investigations=invs,
    )


@router.get("/5")
def phase5(slug: str, request: Request, db: Session = Depends(get_db),
           form: str = Query("m15"), q: str | None = Query(None)):
    c, _ = _ctx(db, slug)
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 5))

    counts = {
        "m15": db.scalar(select(func.count()).select_from(Mau15Row).where(Mau15Row.company_id == c.id)) or 0,
        "m15a": db.scalar(select(func.count()).select_from(Mau15aRow).where(Mau15aRow.company_id == c.id)) or 0,
        "m16": db.scalar(select(func.count()).select_from(Mau16Row).where(Mau16Row.company_id == c.id)) or 0,
        "tp_xk": db.scalar(
            select(func.count(func.distinct(Mau16Row.tp_code))).where(Mau16Row.company_id == c.id)
        ) or 0,
    }

    rows = []
    if form == "m15":
        stmt = select(Mau15Row).where(Mau15Row.company_id == c.id)
        if q:
            stmt = stmt.where(Mau15Row.material.ilike(f"%{q}%"))
        rows = db.scalars(stmt.limit(100)).all()
    elif form == "m15a":
        stmt = select(Mau15aRow).where(Mau15aRow.company_id == c.id)
        if q:
            stmt = stmt.where(Mau15aRow.material.ilike(f"%{q}%"))
        rows = db.scalars(stmt.limit(100)).all()
    elif form == "m16":
        stmt = select(Mau16Row).where(Mau16Row.company_id == c.id)
        if q:
            stmt = stmt.where((Mau16Row.tp_code.ilike(f"%{q}%")) | (Mau16Row.nvl_code.ilike(f"%{q}%")))
        rows = db.scalars(stmt.limit(100)).all()

    n_cycles = db.scalar(
        select(func.count(func.distinct(BomCycle.scc_label))).where(BomCycle.company_id == c.id)
    ) or 0
    n_cycle_nodes = db.scalar(
        select(func.count()).select_from(BomCycle).where(BomCycle.company_id == c.id)
    ) or 0

    return request.app.state.render(
        request, "phases/phase5.html",
        company=c, run=run, counts=counts, form=form, q=q or "", rows=rows,
        n_cycles=n_cycles, n_cycle_nodes=n_cycle_nodes,
    )


@router.get("/5/cycles")
def phase5_cycles(slug: str, request: Request, db: Session = Depends(get_db)):
    c, _ = _ctx(db, slug)

    cycles_rows = db.scalars(
        select(BomCycle).where(BomCycle.company_id == c.id).order_by(desc(BomCycle.scc_size), BomCycle.scc_label)
    ).all()
    grouped: dict = {}
    for r in cycles_rows:
        grouped.setdefault(r.scc_label, {"label": r.scc_label, "size": r.scc_size, "nodes": []})["nodes"].append(r.material)
    sccs = list(grouped.values())

    edges_rows = db.scalars(
        select(BomCycleEdge).where(BomCycleEdge.company_id == c.id)
    ).all()
    edges_by_label: dict = defaultdict(list)
    for e in edges_rows:
        edges_by_label[e.scc_label].append({
            "src": e.src, "dst": e.dst, "norm": e.norm,
            "consumed": e.consumed, "produced": e.produced,
        })
    for s in sccs:
        s["edges"] = edges_by_label.get(s["label"], [])

    return request.app.state.render(
        request, "phases/phase5_cycles.html", company=c, sccs=sccs,
    )


@router.get("/6")
def phase6(slug: str, request: Request, db: Session = Depends(get_db)):
    c, _ = _ctx(db, slug)
    run = db.scalar(select(PhaseRun).where(PhaseRun.company_id == c.id, PhaseRun.phase_no == 6))
    results = db.scalars(
        select(ValidationResult).where(ValidationResult.company_id == c.id).order_by(ValidationResult.test_code)
    ).all()
    n_pass = sum(1 for r in results if r.status == "pass")
    return request.app.state.render(
        request, "phases/phase6.html",
        company=c, run=run, results=results, n_pass=n_pass, n_total=len(results),
    )

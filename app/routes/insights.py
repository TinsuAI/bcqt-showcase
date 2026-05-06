"""Trang truy vết NVL + phát hiện rủi ro + nhật ký xử lý + runs + rules."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BomEdge, BomNode, Mau16Row, NvlTraceability, PipelineRun, ProcessLog, RiskFinding
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


@router.get("/bom")
def bom(slug: str, request: Request, db: Session = Depends(get_db),
        tp: str | None = Query(None)):
    c = get_company_or_404(db, slug)

    # Tổng quan: số TP có data BOM
    n_tp_total = db.scalar(
        select(func.count(func.distinct(BomNode.tp_code)))
        .where(BomNode.company_id == c.id)
    ) or 0
    n_nodes_total = db.scalar(
        select(func.count()).select_from(BomNode).where(BomNode.company_id == c.id)
    ) or 0
    n_edges_total = db.scalar(
        select(func.count()).select_from(BomEdge).where(BomEdge.company_id == c.id)
    ) or 0

    # 6 TP đại diện cho gallery (chain 2 cấp, vừa đủ — show first-time)
    featured_codes = ["MGM1139-252", "MEP2554-01US", "MGM1200-406",
                      "MGM1212-406", "MGM0996-USA", "MGM1036-USA"]
    gallery = []
    for code in featured_codes:
        root = db.scalar(
            select(BomNode).where(
                BomNode.company_id == c.id, BomNode.tp_code == code, BomNode.level == 0
            )
        )
        if not root:
            continue
        n_nodes = db.scalar(
            select(func.count()).select_from(BomNode)
            .where(BomNode.company_id == c.id, BomNode.tp_code == code)
        ) or 0
        n_edges = db.scalar(
            select(func.count()).select_from(BomEdge)
            .where(BomEdge.company_id == c.id, BomEdge.tp_code == code)
        ) or 0
        max_level = db.scalar(
            select(func.max(BomNode.level))
            .where(BomNode.company_id == c.id, BomNode.tp_code == code)
        ) or 0
        gallery.append({
            "code": code, "description": root.description or "",
            "n_nodes": n_nodes, "n_edges": n_edges, "max_level": max_level,
        })

    # Resolve selected TP — accept any TP có trong DB
    selected_tp = None
    if tp:
        exists = db.scalar(
            select(BomNode.tp_code)
            .where(BomNode.company_id == c.id, BomNode.tp_code == tp, BomNode.level == 0)
        )
        if exists:
            selected_tp = tp
    if not selected_tp and gallery:
        selected_tp = gallery[0]["code"]

    nodes = []
    edges = []
    nodes_json: list[dict] = []
    edges_json: list[dict] = []
    if selected_tp:
        nodes = db.scalars(
            select(BomNode)
            .where(BomNode.company_id == c.id, BomNode.tp_code == selected_tp)
            .order_by(BomNode.level, BomNode.material)
        ).all()
        edges = db.scalars(
            select(BomEdge)
            .where(BomEdge.company_id == c.id, BomEdge.tp_code == selected_tp)
        ).all()
        nodes_json = [
            {
                "material": n.material,
                "description": n.description or "",
                "level": n.level,
                "category": n.category or "",
            }
            for n in nodes
        ]
        edges_json = [
            {"src": e.src, "dst": e.dst, "norm": e.norm}
            for e in edges
        ]

    # Search miss?
    search_miss = bool(tp and not selected_tp)

    return request.app.state.render(
        request, "insights/bom.html",
        company=c, gallery=gallery, selected_tp=selected_tp,
        nodes=nodes, edges=edges,
        nodes_json=nodes_json, edges_json=edges_json,
        n_tp_total=n_tp_total, n_nodes_total=n_nodes_total,
        n_edges_total=n_edges_total,
        search_miss=search_miss, search_q=tp or "",
    )


@router.get("/runs")
def runs(slug: str, request: Request, db: Session = Depends(get_db)):
    c = get_company_or_404(db, slug)
    items = db.scalars(
        select(PipelineRun)
        .where(PipelineRun.company_id == c.id)
        .order_by(desc(PipelineRun.run_no))
    ).all()
    total_seconds = sum(r.duration_s for r in items) or 0
    return request.app.state.render(
        request, "insights/runs.html",
        company=c, runs=items, total_seconds=total_seconds,
    )


# Rules: read-only viewer cho YAML config
RULE_FILES = [
    {
        "key": "movement_types",
        "title": "Loại chuyển động kho SAP",
        "subtitle": "MvT — chiều nhập/xuất, có vào BCQT hay không",
        "phase": "P1, P3, P5",
        "regulation": "SAP standard",
    },
    {
        "key": "customs_types",
        "title": "Loại hình hải quan",
        "subtitle": "Mã loại hình áp dụng cho BCCT (E11/E13/E15/E42…)",
        "phase": "P1, P3, P5",
        "regulation": "QĐ 1357/QĐ-TCHQ",
    },
    {
        "key": "QD1357_reference",
        "title": "Bảng tham chiếu QĐ 1357",
        "subtitle": "40 mã loại hình chính thức (16 XK + 24 NK)",
        "phase": "P3, P4",
        "regulation": "QĐ 1357/QĐ-TCHQ",
    },
    {
        "key": "material_classification",
        "title": "Phân loại vật tư",
        "subtitle": "Quy tắc map TK kế toán + Material Type → NVL/BTP/TP/CCDC",
        "phase": "P2",
        "regulation": "Nguyên tắc nội bộ",
    },
    {
        "key": "settlement_overrides",
        "title": "Override khi lập mẫu quyết toán",
        "subtitle": "T02 UOM ×1000, dual-source FIFO, scrap allocation",
        "phase": "P5",
        "regulation": "TT 38/2015 + nội bộ",
    },
    {
        "key": "settlement_columns",
        "title": "Cấu hình cột Mẫu 15/15a/16",
        "subtitle": "Mapping internal column → tên cột nộp HQ",
        "phase": "P5",
        "regulation": "PL II + V TT 39/2018",
    },
    {
        "key": "known_issues_2025",
        "title": "Vấn đề đã biết — kỳ 2025",
        "subtitle": "Danh sách bug/issue đã phát hiện và cách xử lý",
        "phase": "P3, P4",
        "regulation": None,
    },
]


def _load_yaml_file(key: str) -> tuple[str | None, int]:
    """Load YAML từ Johnson config dir (read-only)."""
    path = Path("/home/vp/workspace/client/Johnson/config") / f"{key}.yaml"
    if not path.exists():
        return None, 0
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, 0
    return text, len(text.splitlines())


@router.get("/rules")
def rules(slug: str, request: Request, db: Session = Depends(get_db),
          file: str | None = Query(None)):
    c = get_company_or_404(db, slug)
    selected = None
    yaml_text = None
    line_count = 0
    if file:
        for r in RULE_FILES:
            if r["key"] == file:
                selected = r
                break
        if selected:
            yaml_text, line_count = _load_yaml_file(file)
    return request.app.state.render(
        request, "insights/rules.html",
        company=c, files=RULE_FILES,
        selected=selected, yaml_text=yaml_text, line_count=line_count,
    )

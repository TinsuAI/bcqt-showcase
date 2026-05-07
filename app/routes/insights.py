"""Trang truy vết NVL + phát hiện rủi ro + nhật ký xử lý + runs + rules."""

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    BcctRecord,
    BomEdge,
    BomNode,
    CrosscheckRow,
    Material,
    Mau15aRow,
    Mau15Row,
    Mau16Row,
    Mb51Movement,
    NvlTraceability,
    PipelineRun,
    ProcessLog,
    RiskFinding,
)
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


@router.get("/material/{code}")
def material_profile(slug: str, code: str, request: Request, db: Session = Depends(get_db)):
    """Hồ sơ 1 mã — single source of truth: master + MB51 + BCCT + M15/15a/16 + truy vết + BOM."""
    c = get_company_or_404(db, slug)

    # Master classification
    master = db.scalar(
        select(Material).where(Material.company_id == c.id, Material.code == code)
    )

    # MB51 movements summary (count + qty by MvT)
    mb51_summary = db.execute(
        select(
            Mb51Movement.movement_type,
            func.count(),
            func.sum(Mb51Movement.quantity),
        )
        .where(Mb51Movement.company_id == c.id, Mb51Movement.material == code)
        .group_by(Mb51Movement.movement_type)
        .order_by(desc(func.count()))
    ).all()
    mb51_total = db.scalar(
        select(func.count()).select_from(Mb51Movement)
        .where(Mb51Movement.company_id == c.id, Mb51Movement.material == code)
    ) or 0
    mb51_sample = db.scalars(
        select(Mb51Movement)
        .where(Mb51Movement.company_id == c.id, Mb51Movement.material == code)
        .order_by(desc(Mb51Movement.posting_date))
        .limit(10)
    ).all()

    # BCCT records (HQ thực ra dùng material_code khác — best effort)
    bcct_records = db.scalars(
        select(BcctRecord)
        .where(BcctRecord.company_id == c.id, BcctRecord.material == code)
        .limit(15)
    ).all()
    bcct_total = db.scalar(
        select(func.count()).select_from(BcctRecord)
        .where(BcctRecord.company_id == c.id, BcctRecord.material == code)
    ) or 0

    # M15 (NVL) row
    m15 = db.scalar(
        select(Mau15Row).where(Mau15Row.company_id == c.id, Mau15Row.material == code)
    )

    # M15a (TP XK) row
    m15a = db.scalar(
        select(Mau15aRow).where(Mau15aRow.company_id == c.id, Mau15aRow.material == code)
    )

    # M16 — nếu là TP: list NVL inputs
    m16_as_tp = db.scalars(
        select(Mau16Row)
        .where(Mau16Row.company_id == c.id, Mau16Row.tp_code == code)
        .order_by(desc(Mau16Row.norm))
        .limit(50)
    ).all()
    # M16 — nếu là NVL: list TP outputs
    m16_as_nvl = db.scalars(
        select(Mau16Row)
        .where(Mau16Row.company_id == c.id, Mau16Row.nvl_code == code)
        .order_by(desc(Mau16Row.norm))
        .limit(20)
    ).all()

    # Truy vết NVL row
    trace = db.scalar(
        select(NvlTraceability).where(
            NvlTraceability.company_id == c.id, NvlTraceability.material == code
        )
    )

    # Có trong BOM curated không?
    has_bom_graph = db.scalar(
        select(BomNode.tp_code).where(
            BomNode.company_id == c.id, BomNode.tp_code == code, BomNode.level == 0
        )
    ) is not None

    # Phát hiện vai trò để hiển thị header badge
    role = "Khác"
    if m15a:
        role = "Thành phẩm xuất khẩu"
    elif master and master.category == "TP":
        role = "Thành phẩm"
    elif master and master.category in ("BTP_SX", "BTP_NM"):
        role = "Bán thành phẩm"
    elif master and master.category == "NVL":
        role = "Nguyên vật liệu"
    elif master and master.category == "CCDC":
        role = "CCDC"

    # Auto-gen "Vì sao" — diễn giải tại sao mã được/không được đưa vào mẫu nào
    explanations: list[dict] = []
    if master:
        if master.has_conflict:
            explanations.append({
                "tone": "warning",
                "title": "Có mâu thuẫn phân loại nội bộ",
                "body": (
                    f"Tài khoản kế toán ({master.gl_account or '—'}) và loại vật tư SAP "
                    f"({master.material_type or '—'}) đang đề xuất phân loại khác nhau. "
                    "Pipeline áp ưu tiên hành vi MB51, kết quả cuối: "
                    f"{master.category or '—'}. Đã ghi vào nhật ký xử lý."
                ),
            })
        if master.category == "NVL":
            explanations.append({
                "tone": "info",
                "title": "Đưa vào Mẫu 15 — nguyên vật liệu",
                "body": (
                    f"Nguyên liệu (TK {master.gl_account or '—'}, loại SAP {master.material_type or '—'}). "
                    "Mẫu 15 ghi nhận nhập-xuất-tồn theo TT 39/2018 Phụ lục V."
                ),
            })
        elif master.category == "TP":
            if m15a:
                explanations.append({
                    "tone": "success",
                    "title": "Đưa vào Mẫu 15a + Mẫu 16 — thành phẩm xuất khẩu",
                    "body": (
                        "Có nhập kho thành phẩm và có xuất khẩu E42. "
                        "Mẫu 15a ghi nhập-xuất-tồn TP, Mẫu 16 ghi định mức truy ngược về NVL gốc."
                    ),
                })
            else:
                explanations.append({
                    "tone": "neutral",
                    "title": "Là thành phẩm nhưng chưa xuất khẩu trong kỳ",
                    "body": "Không xuất hiện trên Mẫu 15a (kỳ này không có tờ khai E42 chứa mã).",
                })
        elif master.category in ("BTP_SX", "BTP_NM"):
            explanations.append({
                "tone": "info",
                "title": "Bán thành phẩm — không trực tiếp lên Mẫu 15/15a/16",
                "body": (
                    "Theo TT 39/2018 PL V ghi chú, BTP tự sản xuất không thể hiện chi tiết trên Mẫu 15. "
                    "Pipeline đưa BTP về NVL gốc cấu thành rồi mới ghi vào Mẫu 16. "
                    "Sheet BTP_BALANCE và BOM_Flat trong hồ sơ giải trình lưu chi tiết để cán bộ HQ kiểm tra."
                ),
            })
        elif master.category == "CCDC":
            explanations.append({
                "tone": "neutral",
                "title": "CCDC — không đưa vào Mẫu 15",
                "body": (
                    "Công cụ dụng cụ sử dụng nhiều lần, không cấu thành sản phẩm. "
                    "Theo CV 3304/TCHQ-GSQL, CCDC nhập E13 không thuộc phạm vi BCQT."
                ),
            })
    elif mb51_total > 0:
        explanations.append({
            "tone": "warning",
            "title": "Có hành vi sản xuất nhưng không có Material Master",
            "body": (
                "Mã xuất hiện trong MB51 nhưng không có trong file Material Master MB5B. "
                "Pipeline cờ riêng để doanh nghiệp xác nhận cách phân loại trước khi đưa vào mẫu."
            ),
        })
    if trace and trace.con_lai > 0.5:
        pct = trace.pct_giai_trinh
        explanations.append({
            "tone": "warning",
            "title": f"Truy vết chỉ đạt {pct:.1f}% — còn {trace.con_lai:,.0f} đv chưa giải trình",
            "body": (
                "Phần còn lại có thể là hao hụt cắt dập, phế liệu chưa khai, hoặc sai mapping. "
                "Cần tài liệu kỹ thuật bổ sung khi cán bộ HQ yêu cầu."
            ),
        })

    return request.app.state.render(
        request, "insights/material.html",
        company=c, code=code, role=role, master=master,
        mb51_summary=mb51_summary, mb51_total=mb51_total, mb51_sample=mb51_sample,
        bcct_records=bcct_records, bcct_total=bcct_total,
        m15=m15, m15a=m15a, m16_as_tp=m16_as_tp, m16_as_nvl=m16_as_nvl,
        trace=trace, has_bom_graph=has_bom_graph,
        explanations=explanations,
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


@router.get("/crosscheck")
def crosscheck(slug: str, request: Request, db: Session = Depends(get_db),
               sheet: str = Query("all_imports"), filter: str | None = Query(None)):
    """Tự đối chiếu chéo HQ vs SAP — cho DN soi trước khi HQ soi."""
    c = get_company_or_404(db, slug)

    sheet_meta = {
        "all_imports": {
            "title": "Tổng nhập khẩu (E11/E13/E15/G…)",
            "subtitle": "So lượng nhập trong báo cáo VNACCS với chuyển động nhập kho SAP (MvT 101+102).",
            "sap_label": "SAP nhập kho",
            "cus_label": "HQ nhập (BCCT)",
        },
        "export_e42": {
            "title": "Xuất khẩu E42 (DNCX)",
            "subtitle": "So lượng xuất khẩu E42 trong VNACCS với MvT 901/902 SAP.",
            "sap_label": "SAP xuất khẩu",
            "cus_label": "HQ E42",
        },
        "machinery_e13": {
            "title": "Máy móc E13",
            "subtitle": "So lượng E13 trong VNACCS với SAP (mã có hành vi khác NVL — kiểm tra scope CCDC vs vật tư tiêu hao theo CV 3304).",
            "sap_label": "SAP nhập",
            "cus_label": "HQ E13",
        },
    }
    if sheet not in sheet_meta:
        sheet = "all_imports"

    # Aggregate summary
    summary = db.execute(
        select(
            func.count(),
            func.sum(CrosscheckRow.sap_qty),
            func.sum(CrosscheckRow.cus_qty),
            func.sum(CrosscheckRow.sap_value),
            func.sum(CrosscheckRow.cus_value),
        ).where(CrosscheckRow.company_id == c.id, CrosscheckRow.sheet == sheet)
    ).one()
    n_total, sap_qty_sum, cus_qty_sum, sap_value_sum, cus_value_sum = summary
    sap_qty_sum = float(sap_qty_sum or 0)
    cus_qty_sum = float(cus_qty_sum or 0)

    # Status breakdown
    status_counts = dict(db.execute(
        select(CrosscheckRow.match_status, func.count())
        .where(CrosscheckRow.company_id == c.id, CrosscheckRow.sheet == sheet)
        .group_by(CrosscheckRow.match_status)
    ).all())

    # Mã rủi ro: lệch ≥5% giữa SAP và HQ
    n_risk = db.scalar(
        select(func.count()).select_from(CrosscheckRow).where(
            CrosscheckRow.company_id == c.id,
            CrosscheckRow.sheet == sheet,
            func.abs(CrosscheckRow.qty_diff_pct) >= 5,
        )
    ) or 0
    n_match = db.scalar(
        select(func.count()).select_from(CrosscheckRow).where(
            CrosscheckRow.company_id == c.id,
            CrosscheckRow.sheet == sheet,
            CrosscheckRow.sap_qty != 0, CrosscheckRow.cus_qty != 0,
            func.abs(CrosscheckRow.qty_diff_pct) < 5,
        )
    ) or 0
    n_only_sap = db.scalar(
        select(func.count()).select_from(CrosscheckRow).where(
            CrosscheckRow.company_id == c.id,
            CrosscheckRow.sheet == sheet,
            CrosscheckRow.cus_qty == 0, CrosscheckRow.sap_qty != 0,
        )
    ) or 0
    n_only_hq = db.scalar(
        select(func.count()).select_from(CrosscheckRow).where(
            CrosscheckRow.company_id == c.id,
            CrosscheckRow.sheet == sheet,
            CrosscheckRow.sap_qty == 0, CrosscheckRow.cus_qty != 0,
        )
    ) or 0

    # Filter rows
    stmt = select(CrosscheckRow).where(
        CrosscheckRow.company_id == c.id, CrosscheckRow.sheet == sheet
    )
    filter_label = "Tất cả"
    if filter == "sap_only":
        stmt = stmt.where(CrosscheckRow.cus_qty == 0, CrosscheckRow.sap_qty != 0)
        filter_label = "Chỉ có ở SAP (chưa khai HQ?)"
    elif filter == "customs_only":
        stmt = stmt.where(CrosscheckRow.sap_qty == 0, CrosscheckRow.cus_qty != 0)
        filter_label = "Chỉ có ở HQ (chưa nhập kho SAP?)"
    elif filter == "diff_high":
        stmt = stmt.where(func.abs(CrosscheckRow.qty_diff_pct) >= 5)
        filter_label = "Lệch ≥5%"
    elif filter == "match":
        stmt = stmt.where(
            CrosscheckRow.sap_qty != 0, CrosscheckRow.cus_qty != 0,
            func.abs(CrosscheckRow.qty_diff_pct) < 5,
        )
        filter_label = "Khớp (lệch <5%)"

    rows = db.scalars(stmt.order_by(desc(func.abs(CrosscheckRow.qty_diff))).limit(200)).all()

    return request.app.state.render(
        request, "insights/crosscheck.html",
        company=c, sheet=sheet, sheet_meta=sheet_meta[sheet],
        n_total=n_total or 0,
        sap_qty_sum=sap_qty_sum, cus_qty_sum=cus_qty_sum,
        sap_value_sum=float(sap_value_sum or 0), cus_value_sum=float(cus_value_sum or 0),
        status_counts=status_counts,
        n_risk=n_risk, n_match=n_match, n_only_sap=n_only_sap, n_only_hq=n_only_hq,
        rows=rows, filter=filter or "all", filter_label=filter_label,
    )


@router.get("/methodology")
def methodology(slug: str, request: Request, db: Session = Depends(get_db)):
    c = get_company_or_404(db, slug)
    return request.app.state.render(request, "insights/methodology.html", company=c)


@router.get("/download/{key}")
def download(slug: str, key: str, db: Session = Depends(get_db)):
    """Download whitelist files. Path-traversal safe."""
    get_company_or_404(db, slug)
    info = EXPORT_FILES.get(key)
    if not info:
        raise HTTPException(404, f"Unknown download key: {key}")
    path = EXPORTS_DIR / info["file"]
    if not path.exists():
        raise HTTPException(404, f"File not available on server: {info['file']}")
    return FileResponse(path, media_type=info["mime"], filename=info["file"])


@router.get("/bcqt")
def bcqt(slug: str, request: Request, db: Session = Depends(get_db)):
    """Trang BCQT — preview Mẫu 15/15a/16 + download chính thức."""
    from app.models import Mau15aRow, Mau15Row, Mau16Row
    c = get_company_or_404(db, slug)
    counts = {
        "m15": db.scalar(select(func.count()).select_from(Mau15Row).where(Mau15Row.company_id == c.id)) or 0,
        "m15a": db.scalar(select(func.count()).select_from(Mau15aRow).where(Mau15aRow.company_id == c.id)) or 0,
        "m16": db.scalar(select(func.count()).select_from(Mau16Row).where(Mau16Row.company_id == c.id)) or 0,
        "tp_xk": db.scalar(
            select(func.count(func.distinct(Mau16Row.tp_code))).where(Mau16Row.company_id == c.id)
        ) or 0,
    }
    files_available = {k: (EXPORTS_DIR / v["file"]).exists() for k, v in EXPORT_FILES.items()}
    return request.app.state.render(
        request, "insights/bcqt.html",
        company=c, counts=counts, files_available=files_available, exports=EXPORT_FILES,
    )


@router.get("/dossier")
def dossier(slug: str, request: Request, db: Session = Depends(get_db)):
    """Trang Hồ sơ giải trình — list 12 sheet với mô tả + download."""
    c = get_company_or_404(db, slug)
    sheets = [
        {"key": "Material_Classification", "title": "Phân loại vật tư",
         "desc": "20.064 mã được phân loại NVL/BTP/TP/CCDC, kèm cờ mâu thuẫn nếu có."},
        {"key": "BOM_Direct", "title": "Quan hệ định mức trực tiếp",
         "desc": "35.636 cạnh — từng cặp đầu ra ← đầu vào theo lệnh sản xuất thực tế."},
        {"key": "BOM_Flat", "title": "Định mức sau khi đưa BTP về NVL gốc",
         "desc": "57.054 dòng — quan hệ flatten qua các cấp BTP, dùng để sinh Mẫu 16."},
        {"key": "Order_Detail", "title": "Chi tiết lệnh sản xuất",
         "desc": "107.999 bản ghi — từng lệnh SX với đầu vào và đầu ra."},
        {"key": "T02_Applied", "title": "Áp dụng quy đổi UOM",
         "desc": "Các trường hợp UOM giữa SAP và HQ khác đơn vị (vd KG ↔ MT)."},
        {"key": "Dual_Source_FIFO", "title": "FIFO cho NVL nhiều nguồn",
         "desc": "556 mã có cả nguồn HQ và nội bộ — phân bổ theo trình tự thời gian xuất kho."},
        {"key": "Nguon_Kep_Phan_Bo", "title": "Phân bổ NVL nguồn kép",
         "desc": "Cụ thể số lượng từng kỳ phân về phần qua HQ vs phần nội bộ."},
        {"key": "Conversion_Orders", "title": "Lệnh chuyển đổi phiên bản",
         "desc": "167 lệnh — chuyển đổi 1:1 giữa các phiên bản TP, không tiêu hao NVL mới."},
        {"key": "BOM_Cycles", "title": "Vòng tròn sản xuất",
         "desc": "20 nhóm × 44 mã liên thông qua chuyển đổi phiên bản, đã giải đóng."},
        {"key": "Warnings", "title": "Cảnh báo kỹ thuật",
         "desc": "Các trường hợp ranh giới phát hiện trong khi chạy pipeline."},
        {"key": "Validation", "title": "Kiểm thử bất biến cuối",
         "desc": "9 kiểm thử: bảo toàn khối lượng, khớp HQ, không âm — 9/9 đạt."},
        {"key": "NVL_Traceability", "title": "Truy vết NVL",
         "desc": "4.101 mã NVL: xuất sản xuất → vào TP / khoá tồn / còn lại."},
    ]
    return request.app.state.render(request, "insights/dossier.html", company=c, sheets=sheets)


@router.get("/overview")
def overview(slug: str, request: Request, db: Session = Depends(get_db)):
    """Trang Tổng quan dự án — workflow visual cho audience không kỹ thuật."""
    c = get_company_or_404(db, slug)
    return request.app.state.render(request, "insights/overview.html", company=c)


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


CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "exports"

# Whitelist files có thể download — tránh path traversal
EXPORT_FILES = {
    "mau15": {"file": "Mau_15_NVL_v12.0.csv", "label": "Mẫu 15 — NVL nhập-xuất-tồn", "mime": "text/csv"},
    "mau15a": {"file": "Mau_15a_SP_v12.0.csv", "label": "Mẫu 15a — TP xuất khẩu nhập-xuất-tồn", "mime": "text/csv"},
    "mau16": {"file": "Mau_16_DMTT_v12.0.csv", "label": "Mẫu 16 — Định mức thực tế", "mime": "text/csv"},
    "dossier": {"file": "HO_SO_GIAI_TRINH_v12.0.xlsx", "label": "Hồ sơ giải trình (12 sheet)",
                "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "phase1_pdf": {"file": "BAO_CAO_PHASE_1.pdf", "label": "Báo cáo Phase 1 — Chuẩn hoá", "mime": "application/pdf"},
    "phase2_pdf": {"file": "BAO_CAO_PHASE_2.pdf", "label": "Báo cáo Phase 2 — Bổ sung", "mime": "application/pdf"},
    "phase3_pdf": {"file": "BAO_CAO_PHASE_3.pdf", "label": "Báo cáo Phase 3 — Audit", "mime": "application/pdf"},
    "phase4_pdf": {"file": "BAO_CAO_PHASE_4.pdf", "label": "Báo cáo Phase 4 — Điều tra", "mime": "application/pdf"},
    "phase5_pdf": {"file": "BAO_CAO_PHASE_5_V4.pdf", "label": "Báo cáo Phase 5 — Mẫu QT", "mime": "application/pdf"},
}


def _load_yaml_file(key: str) -> tuple[str | None, int, Any]:
    """Load YAML từ configs/ trong project. Return (text, line_count, parsed_data)."""
    path = CONFIGS_DIR / f"{key}.yaml"
    if not path.exists():
        return None, 0, None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None, 0, None
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        data = None
    return text, len(text.splitlines()), data


def _detect_shape(key: str, data: Any) -> str:
    """Phân tích shape YAML để render đúng:
    - codes_table: dict mã → dict thuộc tính (movement_types, customs_types, QD1357)
    - rules_dict: dict rule → dict (material_classification)
    - column_map: nested dict với list-of-dicts {col,name,label} (settlement_columns)
    - status_groups: 3 nhóm resolved/pending/noise_confirmed (known_issues)
    - generic: fallback recursive tree
    """
    if not isinstance(data, dict) or not data:
        return "generic"

    if key in ("movement_types", "customs_types"):
        return "codes_table"
    if key == "QD1357_reference":
        return "codes_grouped"
    if key == "material_classification":
        return "classification"
    if key == "settlement_columns":
        return "column_map"
    if key == "known_issues_2025":
        return "status_groups"
    return "generic"


def _yaml_to_codes_rows(data: dict) -> list[dict]:
    """Convert dict mã → dict thuộc tính → list rows phẳng."""
    rows = []
    for code, props in data.items():
        if not isinstance(props, dict):
            continue
        rows.append({"code": str(code), **props})
    return rows


def _yaml_to_codes_grouped(data: dict) -> dict[str, list[dict]]:
    """QD1357: group theo field 'group' (EXPORT/IMPORT)."""
    groups: dict[str, list[dict]] = {}
    for code, props in data.items():
        if not isinstance(props, dict):
            continue
        g = str(props.get("group", "OTHER"))
        groups.setdefault(g, []).append({"code": str(code), **props})
    return groups


@router.get("/rules")
def rules(slug: str, request: Request, db: Session = Depends(get_db),
          file: str | None = Query(None), view: str = Query("table")):
    c = get_company_or_404(db, slug)
    selected = None
    yaml_text = None
    line_count = 0
    data = None
    shape = "generic"
    rendered: dict[str, Any] = {}

    if file:
        for r in RULE_FILES:
            if r["key"] == file:
                selected = r
                break
        if selected:
            yaml_text, line_count, data = _load_yaml_file(file)
            shape = _detect_shape(file, data)
            if shape == "codes_table":
                rendered["rows"] = _yaml_to_codes_rows(data)
            elif shape == "codes_grouped":
                rendered["groups"] = _yaml_to_codes_grouped(data)
            elif shape == "classification":
                rendered["rules"] = (data or {}).get("rules", {})
                rendered["type_fallback"] = (data or {}).get("type_fallback", {})
            elif shape == "column_map":
                # data shape: { mau15: { bcqt_columns: [...], working_columns: [...] }, mau15a: ..., mau16: ... }
                rendered["sections"] = data or {}
            elif shape == "status_groups":
                rendered["groups"] = data or {}

    return request.app.state.render(
        request, "insights/rules.html",
        company=c, files=RULE_FILES,
        selected=selected, yaml_text=yaml_text, line_count=line_count,
        shape=shape, view=view, rendered=rendered, data=data,
    )

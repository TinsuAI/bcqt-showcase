"""Seed DB từ output Johnson, anonymized.

Chạy: python -m app.seed.load_demo

- Tạo 3 công ty: 1 từ data thật (anonymized) + 2 mock cho multi-tenant.
- Pull subset có ý nghĩa từ output/*.csv và *.xlsx.
- Idempotent: drop và recreate toàn bộ bảng mỗi lần chạy.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select

from app.config import settings
from app.db import Base, SessionLocal, engine
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
    NvlTraceability,
    PhaseArtifact,
    PhaseRun,
    PipelineRun,
    ProcessLog,
    RawFile,
    RiskFinding,
    ValidationResult,
)

OUT = settings.johnson_output_dir
VER = settings.settlement_version  # v12.0


def reset_schema() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _safe_str(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return str(v)


def _to_date(v) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return pd.to_datetime(v).date()
    except Exception:
        return None


def seed_companies(db) -> Company:
    main = Company(
        slug="fdi-a-bn",
        name="Công ty FDI A — Bắc Ninh",
        customs_office="Hải quan Yên Phong",
        tax_code="2301******",
        industry="Sản xuất thiết bị thể thao / fitness",
        province="Bắc Ninh",
        operations_start=date(2025, 6, 1),
        summary=(
            "Doanh nghiệp chế xuất (DNCX) sản xuất thiết bị thể dục (treadmills, "
            "máy gym) bắt đầu hoạt động T6/2025 tại Bắc Ninh. Quyết toán năm 2025 "
            "theo TT 39/2018 — Mẫu 15/15a/16 nộp Hải quan Yên Phong."
        ),
        is_demo=True,
    )
    mock1 = Company(
        slug="fdi-b-hd",
        name="Công ty FDI B — Hải Dương",
        customs_office="Hải quan Hải Dương",
        tax_code="0801******",
        industry="Sản xuất linh kiện điện tử",
        province="Hải Dương",
        operations_start=date(2024, 1, 1),
        summary="Mock — chưa pull data, dùng để minh hoạ multi-tenant.",
        is_demo=True,
    )
    mock2 = Company(
        slug="fdi-c-vp",
        name="Công ty FDI C — Vĩnh Phúc",
        customs_office="Hải quan Vĩnh Phúc",
        tax_code="2500******",
        industry="Sản xuất phụ tùng ô tô",
        province="Vĩnh Phúc",
        operations_start=date(2023, 5, 1),
        summary="Mock — chưa pull data, dùng để minh hoạ multi-tenant.",
        is_demo=True,
    )
    db.add_all([main, mock1, mock2])
    db.flush()
    return main


def seed_phase_meta(db, company: Company) -> None:
    metrics = {
        1: {
            "name": "Chuẩn hoá & làm sạch",
            "summary": "Nhận file thô SAP MB51 (243K dòng), MB5B (20K mã), VNACCS BCCT (37K dòng). Rename, convert ngày, dedup.",
            "metrics": {"mb51_rows": 243421, "mb5b_materials": 20064, "bcct_rows": 37000},
        },
        2: {
            "name": "Phân tích & bổ sung",
            "summary": "Material Master 20,064 mã — phân loại NVL/BTP/TP/CCDC theo TK kế toán + Material Type. 2,100 mâu thuẫn cờ lại.",
            "metrics": {"materials": 20064, "conflicts": 2100, "btp_nm": 8509, "nvl": 6224, "tp": 2830, "btp_sx": 2437, "ccdc": 64},
        },
        3: {
            "name": "Audit chất lượng dữ liệu",
            "summary": "13 test nội bộ + 5 cross-check (MB51 vs MB5B, MB51 vs BCCT). 18,800 phát hiện trên 5,314 mã (26.5%).",
            "metrics": {"findings": 18800, "materials_flagged": 5314, "tests": 13, "crosschecks": 5},
        },
        4: {
            "name": "Điều tra bất thường",
            "summary": "4 investigation: 4.1 manual review, 4.2 customs-only, 4.3 MvT 122/B13, 4.4 phân loại tĩnh vs hành vi.",
            "metrics": {"profiled": 5596, "auto_ok": 41, "auto_exclude": 13, "review": 36, "manual": 10},
        },
        5: {
            "name": "Lập mẫu quyết toán",
            "summary": "Mẫu 15 (NVL nhập-xuất-tồn), 15a (TP XK), 16 (định mức thực tế). BOM flatten 2 cấp + giải hệ tuyến tính cho 20 vòng tròn.",
            "metrics": {"m15_rows": 4773, "m15a_rows": 517, "m16_rows": 42676, "tp_xk": 517, "cycles": 20, "cycle_nodes": 44},
        },
        6: {
            "name": "Xác thực kết quả",
            "summary": "9 test validate: tổng nhập M15 khớp HQ, tổng XK M15a khớp E42, tổng tiêu hao M16 khớp MvT 261. 9/9 PASS, traceability 99.9%.",
            "metrics": {"tests_total": 9, "tests_pass": 9, "traceability_pct": 99.9},
        },
    }
    for n, d in metrics.items():
        db.add(
            PhaseRun(
                company_id=company.id,
                phase_no=n,
                name=d["name"],
                status="done",
                summary=d["summary"],
                metrics_json=json.dumps(d["metrics"], ensure_ascii=False),
            )
        )


def seed_raw_files(db, company: Company) -> None:
    files = [
        ("mb51", "2025MB51-V1.XLSX", 78_000_000, 243421, 243421),
        ("mb5b", "2025MB5B-V1.XLSX", 12_000_000, 93527, 20064),
        ("bcct", "BaoCaoHangChiTiet năm 2025.xls", 26_000_000, 37000, 37000),
        ("material_master", "2025MB5B-V1.XLSX#Sheet3", 0, 20130, 20064),
    ]
    for kind, name, size, raw, clean in files:
        db.add(
            RawFile(
                company_id=company.id,
                file_kind=kind,
                filename=name,
                size_bytes=size,
                rows_raw=raw,
                rows_clean=clean,
            )
        )


def seed_materials(db, company: Company, limit: int = 5000) -> None:
    f = OUT / "CLEAN_MATERIAL_MASTER.csv"
    if not f.exists():
        return
    df = pd.read_csv(f, dtype=str).head(limit)
    rows = []
    for _, r in df.iterrows():
        cat = r.get("category") or r.get("classification")
        rows.append(
            Material(
                company_id=company.id,
                code=str(r.get("material") or r.get("material_code") or ""),
                description=_safe_str(r.get("description") or r.get("material_description")),
                uom=_safe_str(r.get("uom") or r.get("base_uom")),
                material_type=_safe_str(r.get("material_type")),
                gl_account=_safe_str(r.get("gl_account") or r.get("valuation_class")),
                category=_safe_str(cat),
                has_conflict=bool(r.get("has_conflict") in ("True", "true", "1", True)),
            )
        )
    db.add_all(rows)


def seed_mb51_sample(db, company: Company, limit: int = 3000) -> None:
    f = OUT / "CLEAN_MB51_SAP.csv"
    if not f.exists():
        return
    df = pd.read_csv(f, dtype=str, nrows=limit, low_memory=False)

    def fnum(v):
        try:
            return float(v) if v not in (None, "", "nan") else 0.0
        except Exception:
            return 0.0

    rows = []
    for _, r in df.iterrows():
        rows.append(
            Mb51Movement(
                company_id=company.id,
                posting_date=_to_date(r.get("posting_date")),
                material=str(r.get("material") or "")[:64],
                movement_type=str(r.get("movement_type") or r.get("mvt") or "")[:8],
                quantity=fnum(r.get("quantity")),
                uom=_safe_str(r.get("uom")),
                purchase_order=_safe_str(r.get("purchase_order")),
                production_order=_safe_str(r.get("order") or r.get("production_order")),
                gl_account=_safe_str(r.get("gl_account")),
                amount_vnd=fnum(r.get("amount_vnd") or r.get("amount_lc")),
            )
        )
    db.add_all(rows)


def seed_bcct_sample(db, company: Company, limit: int = 3000) -> None:
    f = OUT / "CLEAN_BCCT.csv"
    if not f.exists():
        return
    df = pd.read_csv(f, dtype=str, nrows=limit, low_memory=False)

    def fnum(v):
        try:
            return float(v) if v not in (None, "", "nan") else 0.0
        except Exception:
            return 0.0

    rows = []
    for _, r in df.iterrows():
        ctype = _safe_str(r.get("customs_type") or r.get("loai_hinh"))
        direction = "import" if ctype and ctype.startswith("E1") else (
            "export" if ctype and ctype.startswith("E4") else None
        )
        rows.append(
            BcctRecord(
                company_id=company.id,
                declaration_date=_to_date(r.get("declaration_date") or r.get("ngay_dang_ky")),
                declaration_no=_safe_str(r.get("declaration_no") or r.get("so_to_khai")),
                customs_type=ctype,
                direction=direction,
                material=_safe_str(r.get("material") or r.get("ma_hang")),
                quantity=fnum(r.get("quantity") or r.get("luong")),
                uom=_safe_str(r.get("uom") or r.get("dvt")),
                amount_usd=fnum(r.get("amount_usd") or r.get("tri_gia")),
            )
        )
    db.add_all(rows)


def seed_audit_findings(db, company: Company) -> None:
    """Tổng hợp phase 3 audit thành findings — pull từ AUDIT_PHASE3.xlsx nếu có."""
    f = OUT / "AUDIT_PHASE3.xlsx"
    if not f.exists():
        return
    try:
        xl = pd.ExcelFile(f)
    except Exception:
        return

    test_sheets = [s for s in xl.sheet_names if re.match(r"^(T\d{2}|XC\d)", s)]
    test_names = {
        "T01": "Trùng PO+material+date", "T02": "UOM mismatch (kg vs g, ×1000)",
        "T03": "GL conflict với material type", "T04": "Timing nhập trước xuất",
        "T05": "Số âm vô lý", "T06": "Ngày posting ngoài T6-T12",
        "T07": "Material không có trong master", "T08": "MvT không trong whitelist",
        "T09": "Order không có output 101", "T10": "Self-consumption cùng order",
        "T11": "Negative stock thời điểm", "T12": "Per-order norm outlier",
        "T13": "Mass conservation MB51",
        "XC1": "MB51 vs MB5B (số lượng)", "XC2": "MB51 vs BCCT (nhập)",
        "XC3": "MB51 vs BCCT (xuất E42)", "XC4": "MB5B vs BCCT (mã)",
        "XC5": "Material Master đầy đủ",
    }
    rows = []
    for sheet in test_sheets:
        try:
            df = pd.read_excel(xl, sheet_name=sheet)
        except Exception:
            continue
        code = sheet
        name = test_names.get(code, sheet)
        for _, r in df.head(50).iterrows():
            sev = "warning"
            if any("critical" in str(c).lower() for c in r.values):
                sev = "critical"
            rows.append(
                AuditFinding(
                    company_id=company.id,
                    test_code=code,
                    test_name=name[:255],
                    severity=sev,
                    material=_safe_str(r.get("material") if "material" in df.columns else None),
                    detail=str(r.to_dict())[:1000],
                    metrics_json=None,
                )
            )
    db.add_all(rows)


def seed_investigations(db, company: Company) -> None:
    items = [
        ("4.1", "Manual review 5,596 mã", "done", 5596,
         "Profile mọi mã có flag từ Phase 3, phân nhóm AUTO_OK / AUTO_EXCLUDE / REVIEW / MANUAL.",
         "41% AUTO_OK, 13% AUTO_EXCLUDE, 36% cần review, 10% manual."),
        ("4.2", "Customs-only — mã có HQ nhưng không có MB51", "done", 71,
         "71 mã null-material trong MB51, 2 mã chỉ có ở HQ.",
         "Đa phần là lỗi nhập liệu SAP — đề xuất Johnson xác nhận."),
        ("4.3", "MvT 122 và mã loại hình B13", "done", 268,
         "MvT 122 = điều chỉnh nhập kho (KHÔNG phải trả hàng NCC). 243/268 mã SAP net khớp HQ import.",
         "sap_net_no_122 = 101+102 only. Q3 (B13) chuyển từ BLOCKING_P5 → xác nhận."),
        ("4.4", "Phân loại tĩnh vs hành vi", "done", 340,
         "340 mã (5.5% active) mâu thuẫn TK kế toán vs hành vi MB51.",
         "Hành vi > Loại VT > TK kế toán. 131/340 giải quyết bằng loại VT, 209 ưu tiên hành vi."),
    ]
    for code, title, status, n, summary, resolution in items:
        db.add(
            Investigation(
                company_id=company.id,
                inv_code=code,
                title=title,
                status=status,
                materials_count=n,
                summary=summary,
                resolution=resolution,
            )
        )


def seed_mau15(db, company: Company) -> None:
    f = OUT / f"Mau_15_NVL_{VER}.csv"
    if not f.exists():
        return
    df = pd.read_csv(f)
    rows = []
    for _, r in df.iterrows():
        rows.append(
            Mau15Row(
                company_id=company.id,
                material=str(r.get("material", ""))[:64],
                description=_safe_str(r.get("material_description")),
                uom=_safe_str(r.get("dvt")),
                ton_dau_ky=float(r.get("ton_dau_ky") or 0),
                nhap_trong_ky=float(r.get("nhap_trong_ky") or 0),
                xuat_san_xuat=float(r.get("xuat_san_xuat") or 0),
                xuat_khac=float(r.get("xuat_khac") or 0),
                ton_cuoi_ky=float(r.get("ton_cuoi_ky") or 0),
            )
        )
    db.add_all(rows)


def seed_mau15a(db, company: Company) -> None:
    f = OUT / f"Mau_15a_SP_{VER}.csv"
    if not f.exists():
        return
    df = pd.read_csv(f)
    rows = []
    for _, r in df.iterrows():
        rows.append(
            Mau15aRow(
                company_id=company.id,
                material=str(r.get("material", ""))[:64],
                description=_safe_str(r.get("material_description")),
                uom=_safe_str(r.get("dvt")),
                ton_dau_ky=float(r.get("ton_dau_ky") or 0),
                nhap_kho=float(r.get("nhap_kho_trong_ky") or r.get("nhap_kho") or 0),
                xuat_khau=float(r.get("xuat_khau") or 0),
                xuat_khac=float(r.get("xuat_khac") or 0),
                ton_cuoi_ky=float(r.get("ton_cuoi_ky") or 0),
            )
        )
    db.add_all(rows)


def seed_mau16(db, company: Company, limit: int = 50000) -> None:
    f = OUT / f"Mau_16_DMTT_{VER}.csv"
    if not f.exists():
        return
    df = pd.read_csv(f).head(limit)
    rows = []
    for _, r in df.iterrows():
        rows.append(
            Mau16Row(
                company_id=company.id,
                tp_code=str(r.get("ma_sp_xk", ""))[:64],
                tp_name=_safe_str(r.get("ten_sp_xk")),
                tp_uom=_safe_str(r.get("dvt_sp")),
                nvl_code=str(r.get("ma_nvl", ""))[:64],
                nvl_name=_safe_str(r.get("ten_nvl")),
                nvl_uom=_safe_str(r.get("dvt_nvl")),
                norm=float(r.get("dinh_muc_thuc_te") or 0),
                note=_safe_str(r.get("ghi_chu")),
            )
        )
    db.add_all(rows)


def seed_bom_cycles(db, company: Company) -> None:
    """Pull từ BOM_Cycles + BOM_Direct trong HO_SO_GIAI_TRINH."""
    f = OUT / f"HO_SO_GIAI_TRINH_{VER}.xlsx"
    if not f.exists():
        return
    try:
        df_cycles = pd.read_excel(f, sheet_name="BOM_Cycles", skiprows=2)
        df_cycles.columns = [c.strip().lower() for c in df_cycles.columns]
        bd = pd.read_excel(f, sheet_name="BOM_Direct")
    except Exception:
        return

    label_col = "nhom_vong_lap" if "nhom_vong_lap" in df_cycles.columns else df_cycles.columns[0]
    size_col = "so_ma_trong_nhom" if "so_ma_trong_nhom" in df_cycles.columns else df_cycles.columns[1]
    mat_col = "ma_vat_tu" if "ma_vat_tu" in df_cycles.columns else df_cycles.columns[2]

    scc_groups: dict[str, list[str]] = defaultdict(list)
    for _, r in df_cycles.iterrows():
        label = _safe_str(r.get(label_col))
        mat = _safe_str(r.get(mat_col))
        if not label or not mat or label == label_col:
            continue
        try:
            size = int(r.get(size_col))
        except Exception:
            continue
        scc_groups[label].append(mat)
        db.add(
            BomCycle(
                company_id=company.id,
                scc_label=label,
                scc_size=size,
                material=mat,
            )
        )

    if not scc_groups or "product" not in bd.columns:
        return

    for label, mats in scc_groups.items():
        mset = set(mats)
        sub = bd[bd["product"].isin(mset) & bd["input_material"].isin(mset)]
        for _, r in sub.iterrows():
            db.add(
                BomCycleEdge(
                    company_id=company.id,
                    scc_label=label,
                    src=str(r["product"]),
                    dst=str(r["input_material"]),
                    norm=float(r.get("norm") or 0),
                    consumed=float(r.get("total_consumed") or 0),
                    produced=float(r.get("total_produced") or 0),
                )
            )


def seed_phase_artifacts(db, company: Company) -> None:
    """File input/output mỗi phase tạo ra — list để show ở per-phase page."""
    items = [
        # Phase 1
        (1, "input", "MB51 thô (SAP)", "2025MB51-V1.XLSX", 243421, 78_000_000, "5 sheet, header TQ"),
        (1, "input", "MB5B thô (SAP)", "2025MB5B-V1.XLSX", 93527, 12_000_000, "3 sheet, có Material Master"),
        (1, "input", "BCCT thô (VNACCS)", "BaoCaoHangChiTiet năm 2025.xls", 37000, 26_000_000, "Định dạng .xls cũ"),
        (1, "output", "MB51 đã sạch", "CLEAN_MB51_SAP.xlsx", 243421, 66_000_000, "Cột EN, dedup"),
        (1, "output", "MB5B đã sạch (chi tiết)", "CLEAN_MB5B_DETAIL.xlsx", 20064, 1_600_000, None),
        (1, "output", "MB5B đã sạch (tổng hợp)", "CLEAN_MB5B_SUMMARY.xlsx", 20064, 5_500, None),
        (1, "output", "BCCT đã sạch", "CLEAN_BCCT.xlsx", 37000, 9_600_000, None),
        # Phase 2
        (2, "input", "MB5B Sheet3 (Material Master thô)", "2025MB5B-V1.XLSX#Sheet3", 20130, 0, None),
        (2, "input", "MB51/MB5B/BCCT đã sạch", "CLEAN_MB51 + CLEAN_MB5B + CLEAN_BCCT", 0, 0, "từ Phase 1"),
        (2, "output", "Material Master phân loại", "CLEAN_MATERIAL_MASTER.xlsx", 20064, 1_700_000, "5 phân loại NVL/BTP/TP/CCDC"),
        (2, "output", "MB5B đã enrich (master meta)", "ENRICHED_MB5B.xlsx", 20064, 1_900_000, "100% match"),
        (2, "output", "MB51 đã enrich", "ENRICHED_MB51.xlsx", 243421, 71_000_000, "74 row null-material"),
        (2, "output", "Báo cáo mâu thuẫn phân loại", "PHAN_LOAI_MAU_THUAN_JOHNSON.xlsx", 2100, 30_000, "cần khách xác nhận"),
        # Phase 3
        (3, "input", "ENRICHED_MB51 + ENRICHED_MB5B + CLEAN_BCCT", "(từ Phase 2)", 0, 0, None),
        (3, "output", "Audit Phase 3 — 13 test", "AUDIT_PHASE3.xlsx", 18800, 790_000, "T01-T13"),
        (3, "output", "Cross-check MB51 vs BCCT", "CROSSCHECK_MB51_BAOCAO.xlsx", 5314, 565_000, None),
        (3, "output", "Cross-check MB51 vs MB5B", "CROSSCHECK_MB51_MB5B.xlsx", 0, 2_300_000, None),
        # Phase 4
        (4, "input", "AUDIT_PHASE3 + CROSSCHECK", "(từ Phase 3)", 0, 0, None),
        (4, "output", "Phase 4 — manual review summary", "MANUAL_REVIEW_SUMMARY.xlsx", 5596, 320_000, "AUTO_OK/EXCLUDE/REVIEW/MANUAL"),
        (4, "output", "Investigation 4.1-4.4", "PHASE4_INVESTIGATION.xlsx", 5596, 2_600_000, None),
        (4, "output", "Inv 4.3 — MvT 122 / B13", "INVESTIGATION_43_MVT122_B13.xlsx", 268, 773_000, None),
        (4, "output", "Inv 4.4 — phân loại tĩnh vs hành vi", "INVESTIGATION_44_STATIC_VS_BEHAVIOR.xlsx", 340, 732_000, None),
        # Phase 5
        (5, "input", "ENRICHED_* + Investigation rules", "(từ Phase 2 + Phase 4)", 0, 0, None),
        (5, "input", "Cấu hình overrides", "settlement_overrides.yaml", 0, 5_000, "T02 + dual-source rules"),
        (5, "output", "Mẫu 15 — NVL", "Mau_15_NVL_v12.0.csv", 4773, 519_000, "nộp HQ"),
        (5, "output", "Mẫu 15a — TP XK", "Mau_15a_SP_v12.0.csv", 517, 41_000, "nộp HQ"),
        (5, "output", "Mẫu 16 — định mức thực tế", "Mau_16_DMTT_v12.0.csv", 42676, 5_000_000, "nộp HQ"),
        (5, "output", "Hồ sơ giải trình", "HO_SO_GIAI_TRINH_v12.0.xlsx", 0, 6_400_000, "12 sheet — lưu nội bộ"),
        (5, "output", "Settlement forms (HQ format)", "SETTLEMENT_FORMS_v12.0.xlsx", 0, 0, "định dạng nộp HQ"),
        # Phase 6
        (6, "input", "Mẫu 15/15a/16 + HO_SO_GIAI_TRINH", "(từ Phase 5)", 0, 0, None),
        (6, "output", "Validation — 9 test", "Validation sheet (HO_SO_v12.0)", 9, 0, "9/9 PASS"),
        (6, "output", "Báo cáo so sánh phiên bản", "COMPARE_v11.3_vs_v12.0.xlsx", 0, 3_900_000, None),
    ]
    for phase, role, label, filename, rows, size, note in items:
        db.add(
            PhaseArtifact(
                company_id=company.id,
                phase_no=phase,
                role=role,
                label=label,
                filename=filename,
                rows=rows or None,
                size_bytes=size or None,
                note=note,
            )
        )


def seed_pipeline_runs(db, company: Company) -> None:
    """Lịch sử chạy pipeline — 8 lần thật từ session note Johnson."""
    runs = [
        (1, "v0.9", "P1-P3", datetime(2026, 3, 1, 9, 14), 1820, "Phạm Vương", "done", 12, "Lần đầu chuẩn hoá data thô"),
        (2, "v1.0", "P1-P3", datetime(2026, 3, 5, 0, 30), 1843, "Phạm Vương", "done", 14, "Tag v1-final, archived"),
        (3, "v2.0", "P2", datetime(2026, 3, 5, 1, 54), 612, "Trần Tú Anh", "done", 4, "Material Master 20.064 mã"),
        (4, "v2.1", "P3-P4", datetime(2026, 3, 6, 2, 17), 1380, "Phạm Vương", "done", 8, "Audit + investigation 4.1"),
        (5, "v3.0", "P4", datetime(2026, 3, 9, 15, 47), 720, "Phạm Vương", "done", 2, "Inv 4.3 MvT 122"),
        (6, "v3.1", "P4", datetime(2026, 3, 9, 16, 5), 542, "Phạm Vương", "done", 2, "Inv 4.4 static vs behavior"),
        (7, "v10.0", "P5", datetime(2026, 3, 22, 8, 20), 480, "Trần Tú Anh", "done", 5, "Mẫu 15/15a/16 first cut"),
        (8, "v11.0", "P5", datetime(2026, 3, 23, 1, 57), 510, "Phạm Vương", "done", 5, "Refactor settlement/ package"),
        (9, "v11.2", "P5", datetime(2026, 3, 30, 8, 54), 488, "Phạm Vương", "done", 5, "M15=4.853, M15a=517, M16=42.678. 8/8 PASS"),
        (10, "v11.3", "P5-P6", datetime(2026, 3, 30, 13, 36), 521, "Trần Tú Anh", "done", 6, "Fix BTP closing stock norm. Traceability 99,4 → 99,9%"),
        (11, "v12.0", "P5-P6", datetime(2026, 3, 30, 21, 35), 492, "Phạm Vương", "done", 7, "Final: 9/9 PASS, M15=4.773, all overrides applied"),
    ]
    for run_no, version, phases, started, duration, actor, status, n_art, note in runs:
        db.add(
            PipelineRun(
                company_id=company.id,
                run_no=run_no,
                version=version,
                phases_label=phases,
                started_at=started,
                duration_s=duration,
                actor=actor,
                status=status,
                artifacts_count=n_art,
                note=note,
            )
        )


def seed_nvl_traceability(db, company: Company) -> None:
    """Pull NVL_Traceability sheet từ HO_SO_GIAI_TRINH v12.0."""
    f = OUT / f"HO_SO_GIAI_TRINH_{VER}.xlsx"
    if not f.exists():
        return
    try:
        df = pd.read_excel(f, sheet_name="NVL_Traceability", skiprows=2)
    except Exception:
        return
    rows = []
    for _, r in df.iterrows():
        mat = _safe_str(r.get("material"))
        if not mat or mat == "TỔNG":
            continue
        rows.append(
            NvlTraceability(
                company_id=company.id,
                material=mat[:64],
                description=_safe_str(r.get("material_description")),
                uom=None,
                xuat_sx=float(r.get("xuat_sx") or 0),
                cho_xuat_khau=float(r.get("cho_xuat_khau") or 0),
                trong_tp_ton=float(r.get("trong_tp_ton") or 0),
                trong_btp_ton=float(r.get("trong_btp_ton") or 0),
                giai_trinh=float(r.get("giai_trinh") or 0),
                con_lai=float(r.get("con_lai") or 0),
                pct_giai_trinh=float(r.get("pct_giai_trinh") or 0),
            )
        )
    db.add_all(rows)


def seed_risks(db, company: Company) -> None:
    """Top rủi ro nghiệp vụ — pain point bán hàng. Số liệu từ pipeline thật của Johnson."""
    risks = [
        {
            "code": "R01",
            "title": "404 mã NVL có dấu hiệu under-count định mức",
            "severity": "high",
            "category": "Định mức (Mẫu 16)",
            "materials_count": 404,
            "money_impact_vnd": None,
            "description": (
                "404 mã NVL có dấu hiệu thiếu trong định mức công bố — tổng tiêu hao thực tế "
                "ghi nhận trên SAP cao hơn tổng định mức × số lượng TP xuất khẩu. Khoảng chênh "
                "có thể là (a) phế liệu, hao hụt chưa khai; (b) định mức công bố chưa đủ; "
                "(c) sai mapping NVL ↔ TP khi build BOM."
            ),
            "if_ignored": (
                "Hải quan đối chiếu Mẫu 16 với MB51 → phát hiện chênh → yêu cầu giải trình. "
                "Nếu không giải trình được, có thể bị áp giả định 'sử dụng sai mục đích' theo "
                "Đ60 TT 38/2015 → truy thu thuế NK + phạt 10-20% giá trị NVL."
            ),
            "resolution": (
                "Mỗi mã trong 404 đã có log truy vết (sheet NVL_Traceability) — đối chiếu thực tế "
                "trên dây chuyền hoặc bổ sung định mức phế liệu vào Mẫu 16 trước khi nộp."
            ),
            "regulation_ref": "TT 38/2015 Đ55 + Đ60",
        },
        {
            "code": "R02",
            "title": "2.100 mã có mâu thuẫn phân loại nội bộ (master data)",
            "severity": "high",
            "category": "Master data",
            "materials_count": 2100,
            "money_impact_vnd": None,
            "description": (
                "Tài khoản kế toán nói A (vd 12150000 = NVL) nhưng Material Type SAP nói B "
                "(vd HALB = bán thành phẩm). 1.781 mã GL=12150000 + type=HALB (linh kiện mua "
                "ngoài đang treo trên TK NVL); 293 mã GL=12130003 + type=ROH (NVL treo trên "
                "TK BTP ngoại mua). 26 mã pattern khác."
            ),
            "if_ignored": (
                "Mẫu 15 và Mẫu 16 sẽ hiểu khác nhau về cùng một mã → số liệu nhập-xuất-tồn "
                "không khớp → không defensible khi thanh tra."
            ),
            "resolution": (
                "Đã chuẩn bị danh sách 2.100 mã. Yêu cầu phòng kế toán + phòng kho "
                "rà soát đồng thuận, thống nhất cách hiểu trước khi sang Phase 5."
            ),
            "regulation_ref": "Nguyên tắc kế toán + chuẩn SAP",
        },
        {
            "code": "R03",
            "title": "20 vòng tròn sản xuất TP A ↔ B ↔ C — không thể flatten BOM thường",
            "severity": "medium",
            "category": "BOM / định mức",
            "materials_count": 44,
            "money_impact_vnd": None,
            "description": (
                "44 mã TP rơi vào 20 cụm liên thông mạnh (Tarjan SCC): nhỏ nhất 2-node, lớn "
                "nhất 4-node (MGM1114-02 ↔ -08 ↔ -23 ↔ -39). Thực chất là 'chuyển đổi phiên "
                "bản' (US ↔ EU ↔ ASIA) — phiên bản này tháo nhãn dán nhãn phiên bản kia."
            ),
            "if_ignored": (
                "Topological sort phá sản, tính định mức bị deadlock — hoặc bỏ qua các mã "
                "này (thiếu data trong Mẫu 16) hoặc tính trùng (overcount)."
            ),
            "resolution": (
                "Pipeline phát hiện và giải bằng hệ tuyến tính (I − C)·X = K trên mỗi SCC. "
                "Đã verify ρ(C) < 1 cho tất cả 20 SCC, hệ số khuếch đại 1.002–2.0. Có log "
                "`Conversion_Orders` liệt kê 167 lệnh chuyển đổi."
            ),
            "regulation_ref": "TT 38/2015 Đ55 (định mức bình quân thực tế)",
        },
        {
            "code": "R04",
            "title": "Residual 6.619 đơn vị NVL không truy được vào TP nào",
            "severity": "medium",
            "category": "Truy vết",
            "materials_count": 0,
            "quantity_impact": 6619,
            "money_impact_vnd": None,
            "description": (
                "Trong 4.757.304 đơn vị NVL xuất sản xuất, đã giải trình được 4.750.685 đơn "
                "vị (99,9%) vào TP xuất khẩu / TP tồn / BTP tồn. Còn 6.619 đơn vị (~0,14%) "
                "không truy được. Phân tích cho thấy 79% từ 3 mã thép tấm SPHC — đặc thù "
                "hao hụt cắt dập."
            ),
            "if_ignored": (
                "Hải quan có thể coi 0,14% là 'thất thoát NVL' → áp truy thu thuế NK. "
                "Mức 0,14% thường được chấp nhận nếu giải trình được nguồn gốc (hao hụt cắt)."
            ),
            "resolution": (
                "Bổ sung tài liệu kỹ thuật về tỉ lệ hao hụt cắt dập thép tấm (industry "
                "standard 1-3%) làm chứng cứ giải trình."
            ),
            "regulation_ref": "TT 38/2015 Đ60 + TT 121/2025 (hao hụt)",
        },
        {
            "code": "R05",
            "title": "9 câu hỏi quan trọng về quy tắc nghiệp vụ chưa có phản hồi",
            "severity": "high",
            "category": "Quy tắc",
            "materials_count": 0,
            "money_impact_vnd": None,
            "description": (
                "Q1-Q5 BLOCKING_P5 (UOM ×1000, E11/E13 overlap, B13, NVL không nhập, HALB "
                "trên 12150000). Q6-Q8 BLOCKING_SUBMISSION (multi-type, HS mismatch, "
                "negative stock). Q9 NON_BLOCKING (MvT 903)."
            ),
            "if_ignored": (
                "Submit Mẫu 15/15a/16 dựa trên giả định một chiều — nếu giả định sai, toàn "
                "bộ báo cáo phải làm lại từ Phase 5."
            ),
            "resolution": (
                "Đã gửi danh sách câu hỏi cho khách qua doc CAU_HOI_CHO_JOHNSON.pdf. "
                "Đợi phản hồi rồi áp rule vào pipeline run kế tiếp."
            ),
            "regulation_ref": None,
        },
        {
            "code": "R06",
            "title": "340 mã có hành vi MB51 mâu thuẫn với phân loại tĩnh (TK kế toán)",
            "severity": "medium",
            "category": "Phân loại",
            "materials_count": 340,
            "money_impact_vnd": None,
            "description": (
                "340 mã (5,5% mã active) có TK kế toán nói X nhưng hành vi sản xuất thực tế "
                "(input/output trong MB51) cho thấy là Y. Top: 106 BTP_NM→BTP_SX, 82 "
                "BTP_SX→NVL, 81 TP→BTP_SX. 131 mã giải quyết được bằng Material Type, 209 "
                "mã cả TK + type đều sai → ưu tiên hành vi."
            ),
            "if_ignored": (
                "Lập Mẫu 15/15a sai phân loại → mã đáng lẽ không vào BCQT vẫn được khai → "
                "lệch số liệu, mất uy tín."
            ),
            "resolution": (
                "Pipeline áp quy tắc 'Hành vi > Loại VT > TK kế toán' cho 340 mã, có log "
                "kiểm tra. Đã chốt với khách trong session 09/03."
            ),
            "regulation_ref": "TT 38/2015 + thực tiễn",
        },
        {
            "code": "R07",
            "title": "Nguy cơ scope CCDC (TK 12200002) — vào BCQT hay không?",
            "severity": "medium",
            "category": "Scope",
            "materials_count": 64,
            "money_impact_vnd": None,
            "description": (
                "64 mã trên TK 12200002 (CCDC theo kế toán) có hành vi tiêu hao giống NVL. "
                "CV 3304/TCHQ-GSQL phân biệt rõ: nếu nhập E11/E15 → vật tư tiêu hao (vào "
                "BCQT); nếu nhập E13 → CCDC thật (KHÔNG vào BCQT)."
            ),
            "if_ignored": (
                "Khai sai scope: hoặc thiếu (nếu thực chất là VT tiêu hao mà không khai) → "
                "truy thu, hoặc thừa (nếu CCDC mà khai) → bị bác."
            ),
            "resolution": (
                "Pipeline check loại hình từng PO: E11/E15 → đưa vào, E13 → loại. Đã verify "
                "cho từng mã trong 64 mã CCDC."
            ),
            "regulation_ref": "CV 3304/TCHQ-GSQL (27/5/2019)",
        },
    ]
    for r in risks:
        db.add(RiskFinding(company_id=company.id, **r))


def seed_process_logs(db, company: Company) -> None:
    """Nhật ký xử lý — kể chuyện ai làm gì lúc nào (read-only, không tương tác)."""
    logs = [
        (date(2026, 3, 5), "Trần Tú Anh", "PTDL", 1, "Chốt rule clean MB51 + MB5B + BCCT",
         "Confirm: column rename TQ → EN, dedup theo material+date+order, drop garbage rows. Output: CLEAN_MB51 243.421 dòng, CLEAN_MB5B 20.064 mã."),
        (date(2026, 3, 5), "Phạm Vương", "PTDL", 2, "Hoàn tất phân loại Material Master 20.064 mã",
         "Pipeline áp rule TK kế toán làm gốc, Material Type xác minh. Phát hiện 2.100 mâu thuẫn (1.781 HALB+12150000, 293 ROH+12130003). Cờ riêng để hỏi khách."),
        (date(2026, 3, 5), "Trang", "BA", 3, "Audit 13 test + 5 cross-check hoàn tất",
         "18.800 finding trên 5.314 mã. Top finding: T02 UOM mismatch (×1000 g/kg), T11 negative stock thời điểm, X02 MB51 vs BCCT lệch tổng nhập."),
        (date(2026, 3, 6), "Ms. Duyên", "Trưởng nhóm", None, "Đề xuất framework BOM flatten",
         "Quyết định: BTP tự SX không lên Mẫu 15/15a/16 — flatten về NVL gốc theo TT 39/2018. 117 TP dual-role mỗi cái có Mẫu 16 riêng + flatten vào TP cha."),
        (date(2026, 3, 9), "Phạm Vương", "PTDL", 4, "Investigation 4.3 — MvT 122 / mã loại hình B13",
         "Kết luận: MvT 122 = điều chỉnh nhập kho (KHÔNG phải trả hàng NCC). 243/268 mã SAP net (101+102) khớp HQ import. Q3 chuyển BLOCKING_P5 → resolved."),
        (date(2026, 3, 9), "Phạm Vương", "PTDL", 4, "Investigation 4.4 — phân loại tĩnh vs hành vi",
         "340 mã (5,5%) mâu thuẫn. 131 giải quyết bằng Material Type, 209 mã cả TK + type sai. Áp quy tắc 'Hành vi > Loại VT > TK kế toán'."),
        (date(2026, 3, 22), "Ms. Duyên", "Trưởng nhóm", 2, "Xác nhận 1.781 mã HALB trên TK 12150000 → giữ NVL",
         "Lý do: linh kiện mua ngoài kế toán treo trên TK NVL theo quy ước nội bộ. Hành vi sử dụng giống NVL. Phase 5 áp dụng phân loại NVL cho nhóm này."),
        (date(2026, 3, 23), "Phạm Vương", "PTDL", 5, "Phase 5 v11.2 — sinh Mẫu 15/15a/16",
         "Mẫu 15: 4.853 dòng. Mẫu 15a: 517 mã. Mẫu 16: 42.678 dòng (517 TP). 8/8 test PASS. NVL Traceability 99,4%."),
        (date(2026, 3, 24), "Trần Tú Anh", "PTDL", 5, "Phát hiện 20 vòng tròn sản xuất + giải bằng hệ tuyến tính",
         "Tarjan SCC tìm 20 SCC (44 mã). Lớn nhất 4-node MGM1114-*. Solver (I − C)·X = K: tất cả ρ(C) < 1, hệ số khuếch đại 1.002 – 2.0. Critic review pass."),
        (date(2026, 3, 25), "Trần Tú Anh", "PTDL", 5, "Domain expert + critic review — rework norm",
         "Verify TT 38/2015 + TT 39/2018 + TT 121/2025: self-loop solver là cách đúng để xử lý rework. Không có khoảng trống pháp lý A→A. Approved."),
        (date(2026, 3, 30), "Phạm Vương", "PTDL", 5, "Phase 5 v11.3 — fix BTP closing stock norm",
         "Bug: BTP tồn cuối tính sai norm khi flatten. Fix → traceability 99,4% → 99,9% (residual 30.652 → 6.619)."),
        (date(2026, 3, 30), "Trần Tú Anh", "PTDL", 5, "Phase 5 v12.0 — chốt tất cả overrides",
         "Áp tất cả T02/UOM rule, dual-source FIFO, source_config. M15=4.773, M15a=517, M16=42.676 (517 TP). 9/9 validation PASS."),
        (date(2026, 3, 30), "Phạm Vương", "PTDL", 6, "Validate cuối — 9/9 PASS",
         "M15 nhập = HQ import (diff 0,0%). M15a XK = E42 (diff 0,1%). M16 ⊆ M15. Mass conservation ✓. Cycle ρ(C) < 1 ✓. CCDC scope ✓."),
        (date(2026, 4, 19), "Trang", "BA", None, "Tổng hợp 9 câu hỏi blocking gửi Johnson",
         "Q1-Q5 BLOCKING_P5, Q6-Q8 BLOCKING_SUBMISSION, Q9 NON_BLOCKING. Đợi phản hồi từ phòng kế toán Johnson."),
    ]
    for occurred, actor, role, phase_no, action, detail in logs:
        db.add(
            ProcessLog(
                company_id=company.id,
                occurred_on=occurred,
                actor=actor,
                actor_role=role,
                phase_no=phase_no,
                action=action,
                detail=detail,
            )
        )


def seed_validations(db, company: Company) -> None:
    items = [
        ("V1", "Tổng nhập M15 khớp HQ E11/E15", "pass", "758,860,000,000", "758,860,000,000", 0.0),
        ("V2", "Tổng XK M15a khớp HQ E42", "pass", "517 mã", "517 mã", 0.0),
        ("V3", "Tổng tiêu hao M16 ≤ tiêu hao MB51 261", "pass", "4,757,304 đơn vị", "4,750,685 đơn vị", -0.14),
        ("V4", "Mass conservation M15 (đầu+nhập = xuất+cuối)", "pass", "0", "0", 0.0),
        ("V5", "Mass conservation M15a", "pass", "0", "0", 0.0),
        ("V6", "Cycle norm hội tụ (ρ(C) < 1)", "pass", "20/20 SCC", "20/20 SCC", 0.0),
        ("V7", "Mọi mã M16 có trong M15", "pass", "100%", "100%", 0.0),
        ("V8", "Mọi mã M15a có MvT 901/902", "pass", "517/517", "517/517", 0.0),
        ("V9", "Định mức M16 không âm", "pass", "0 vi phạm", "0 vi phạm", 0.0),
    ]
    for code, name, status, expected, actual, delta in items:
        db.add(
            ValidationResult(
                company_id=company.id,
                test_code=code,
                test_name=name,
                status=status,
                expected=expected,
                actual=actual,
                delta_pct=delta,
                note=None,
            )
        )


def main() -> None:
    print(f"[seed] DB: {settings.database_url}")
    print(f"[seed] OUT: {OUT}, version: {VER}")
    reset_schema()
    with SessionLocal() as db:
        company = seed_companies(db)
        seed_phase_meta(db, company)
        seed_raw_files(db, company)
        seed_materials(db, company)
        seed_mb51_sample(db, company)
        seed_bcct_sample(db, company)
        seed_audit_findings(db, company)
        seed_investigations(db, company)
        seed_mau15(db, company)
        seed_mau15a(db, company)
        seed_mau16(db, company)
        seed_bom_cycles(db, company)
        seed_phase_artifacts(db, company)
        seed_pipeline_runs(db, company)
        seed_nvl_traceability(db, company)
        seed_risks(db, company)
        seed_process_logs(db, company)
        seed_validations(db, company)
        db.commit()

        n = db.scalar(select(Company).where(Company.id == company.id))
        print(f"[seed] OK — main company id={n.id} slug={n.slug}")
        for tbl in (Material, Mb51Movement, BcctRecord, AuditFinding, Investigation,
                    Mau15Row, Mau15aRow, Mau16Row, BomCycle, BomCycleEdge,
                    PhaseArtifact, PipelineRun, NvlTraceability, RiskFinding,
                    ProcessLog, ValidationResult):
            cnt = db.scalar(select(__import__("sqlalchemy").func.count()).select_from(tbl))
            print(f"  {tbl.__tablename__:24s} {cnt:>8d}")


if __name__ == "__main__":
    main()

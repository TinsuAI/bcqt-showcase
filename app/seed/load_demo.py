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
from datetime import date

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
    PhaseRun,
    RawFile,
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
            "summary": "9 test validate: tổng nhập M15 khớp HQ, tổng XK M15a khớp E42, tổng tiêu hao M16 khớp MvT 261. 9/9 PASS, traceability 99.4%.",
            "metrics": {"tests_total": 9, "tests_pass": 9, "traceability_pct": 99.4},
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


def seed_mau16(db, company: Company, limit: int = 5000) -> None:
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


def seed_validations(db, company: Company) -> None:
    items = [
        ("V1", "Tổng nhập M15 khớp HQ E11/E15", "pass", "758,860,000,000", "758,860,000,000", 0.0),
        ("V2", "Tổng XK M15a khớp HQ E42", "pass", "517 mã", "517 mã", 0.0),
        ("V3", "Tổng tiêu hao M16 ≤ tiêu hao MB51 261", "pass", "4,716,730 đơn vị", "4,686,078 đơn vị", -0.65),
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
        seed_validations(db, company)
        db.commit()

        n = db.scalar(select(Company).where(Company.id == company.id))
        print(f"[seed] OK — main company id={n.id} slug={n.slug}")
        for tbl in (Material, Mb51Movement, BcctRecord, AuditFinding, Investigation,
                    Mau15Row, Mau15aRow, Mau16Row, BomCycle, BomCycleEdge, ValidationResult):
            cnt = db.scalar(select(__import__("sqlalchemy").func.count()).select_from(tbl))
            print(f"  {tbl.__tablename__:24s} {cnt:>8d}")


if __name__ == "__main__":
    main()

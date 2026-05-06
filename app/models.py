"""DB schema cho demo BCQT — 6 phase pipeline + multi-tenant."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    customs_office: Mapped[str | None] = mapped_column(String(128))
    tax_code: Mapped[str | None] = mapped_column(String(32))
    industry: Mapped[str | None] = mapped_column(String(128))
    province: Mapped[str | None] = mapped_column(String(64))
    operations_start: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    phase_runs: Mapped[list["PhaseRun"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class PhaseRun(Base):
    """1 bản ghi/phase/công ty — meta + KPI tổng kết."""

    __tablename__ = "phase_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    phase_no: Mapped[int] = mapped_column(Integer)  # 1..6
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/running/done/failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    summary: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[str | None] = mapped_column(Text)  # JSON: free-form KPI

    company: Mapped[Company] = relationship(back_populates="phase_runs")


class RawFile(Base):
    """Tracking file thô input cho Phase 1."""

    __tablename__ = "raw_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    file_kind: Mapped[str] = mapped_column(String(32))  # mb51, mb5b, bcct, material_master
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    rows_raw: Mapped[int] = mapped_column(Integer, default=0)
    rows_clean: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)


class Material(Base):
    """Material Master + classification (Phase 2)."""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(String(512))
    uom: Mapped[str | None] = mapped_column(String(16))
    material_type: Mapped[str | None] = mapped_column(String(16))  # ROH/HALB/FERT/ZCON
    gl_account: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(32))  # NVL/BTP_NM/BTP_SX/TP/CCDC
    has_conflict: Mapped[bool] = mapped_column(default=False)


class Mb51Movement(Base):
    """SAP MB51 movement — sample subset (không load 243K hết)."""

    __tablename__ = "mb51_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    posting_date: Mapped[date | None] = mapped_column(Date)
    material: Mapped[str] = mapped_column(String(64), index=True)
    movement_type: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str | None] = mapped_column(String(16))
    purchase_order: Mapped[str | None] = mapped_column(String(32))
    production_order: Mapped[str | None] = mapped_column(String(32))
    gl_account: Mapped[str | None] = mapped_column(String(32))
    amount_vnd: Mapped[float | None] = mapped_column(Float)


class BcctRecord(Base):
    """Báo Cáo Chi Tiết tờ khai hải quan (VNACCS) — sample."""

    __tablename__ = "bcct_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    declaration_date: Mapped[date | None] = mapped_column(Date)
    declaration_no: Mapped[str | None] = mapped_column(String(32))
    customs_type: Mapped[str | None] = mapped_column(String(8))  # E11/E13/E15/E42/...
    direction: Mapped[str | None] = mapped_column(String(16))  # import/export
    material: Mapped[str | None] = mapped_column(String(64))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    uom: Mapped[str | None] = mapped_column(String(16))
    amount_usd: Mapped[float | None] = mapped_column(Float)


class AuditFinding(Base):
    """Phase 3 audit findings (13 tests + 5 crosschecks)."""

    __tablename__ = "audit_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    test_code: Mapped[str] = mapped_column(String(16))  # T01..T13, X01..X05
    test_name: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16))  # critical/warning/info
    material: Mapped[str | None] = mapped_column(String(64), index=True)
    detail: Mapped[str | None] = mapped_column(Text)
    metrics_json: Mapped[str | None] = mapped_column(Text)


class Investigation(Base):
    """Phase 4 investigations (4.1, 4.2, 4.3, 4.4)."""

    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    inv_code: Mapped[str] = mapped_column(String(16))  # 4.1, 4.2, 4.3, 4.4
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    materials_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)


class Mau15Row(Base):
    """Mẫu 15 — NVL nhập-xuất-tồn."""

    __tablename__ = "mau15_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    material: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(String(512))
    uom: Mapped[str | None] = mapped_column(String(16))
    ton_dau_ky: Mapped[float] = mapped_column(Float, default=0.0)
    nhap_trong_ky: Mapped[float] = mapped_column(Float, default=0.0)
    xuat_san_xuat: Mapped[float] = mapped_column(Float, default=0.0)
    xuat_khac: Mapped[float] = mapped_column(Float, default=0.0)
    ton_cuoi_ky: Mapped[float] = mapped_column(Float, default=0.0)


class Mau15aRow(Base):
    """Mẫu 15a — TP xuất khẩu nhập-xuất-tồn."""

    __tablename__ = "mau15a_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    material: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(String(512))
    uom: Mapped[str | None] = mapped_column(String(16))
    ton_dau_ky: Mapped[float] = mapped_column(Float, default=0.0)
    nhap_kho: Mapped[float] = mapped_column(Float, default=0.0)
    xuat_khau: Mapped[float] = mapped_column(Float, default=0.0)
    xuat_khac: Mapped[float] = mapped_column(Float, default=0.0)
    ton_cuoi_ky: Mapped[float] = mapped_column(Float, default=0.0)


class Mau16Row(Base):
    """Mẫu 16 — định mức thực tế NVL gốc ↔ TP XK."""

    __tablename__ = "mau16_rows"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    tp_code: Mapped[str] = mapped_column(String(64), index=True)
    tp_name: Mapped[str | None] = mapped_column(String(512))
    tp_uom: Mapped[str | None] = mapped_column(String(16))
    nvl_code: Mapped[str] = mapped_column(String(64), index=True)
    nvl_name: Mapped[str | None] = mapped_column(String(512))
    nvl_uom: Mapped[str | None] = mapped_column(String(16))
    norm: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str | None] = mapped_column(String(255))


class BomCycle(Base):
    """Vòng tròn sản xuất — 1 bản ghi/SCC/material."""

    __tablename__ = "bom_cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    scc_label: Mapped[str] = mapped_column(String(255), index=True)
    scc_size: Mapped[int] = mapped_column(Integer)
    material: Mapped[str] = mapped_column(String(64))


class BomCycleEdge(Base):
    """Cạnh trong cycle (cho graph viz)."""

    __tablename__ = "bom_cycle_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    scc_label: Mapped[str] = mapped_column(String(255), index=True)
    src: Mapped[str] = mapped_column(String(64))  # output (parent)
    dst: Mapped[str] = mapped_column(String(64))  # input (child)
    norm: Mapped[float] = mapped_column(Float, default=0.0)
    consumed: Mapped[float] = mapped_column(Float, default=0.0)
    produced: Mapped[float] = mapped_column(Float, default=0.0)


class BomNode(Base):
    """Node trong đồ thị BOM curated — pre-computed cho 6 TP đại diện."""

    __tablename__ = "bom_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    tp_code: Mapped[str] = mapped_column(String(64), index=True)
    material: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(512))
    level: Mapped[int] = mapped_column(Integer)  # 0=TP root, 1=BTP/L1 NVL, 2=L2 NVL beneath BTP
    category: Mapped[str | None] = mapped_column(String(32))  # NVL/BTP_SX/BTP_NM/TP


class BomEdge(Base):
    """Cạnh trong đồ thị BOM curated — output ← input với norm."""

    __tablename__ = "bom_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    tp_code: Mapped[str] = mapped_column(String(64), index=True)
    src: Mapped[str] = mapped_column(String(64))  # parent (output)
    dst: Mapped[str] = mapped_column(String(64))  # child (input)
    norm: Mapped[float] = mapped_column(Float, default=0.0)
    consumed: Mapped[float] = mapped_column(Float, default=0.0)
    produced: Mapped[float] = mapped_column(Float, default=0.0)


class PhaseArtifact(Base):
    """File output mỗi phase tạo ra — có thể tải về."""

    __tablename__ = "phase_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    phase_no: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))  # input / output
    label: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    rows: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255))


class PipelineRun(Base):
    """Lịch sử chạy pipeline — static record, có version."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    run_no: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(16))
    phases_label: Mapped[str] = mapped_column(String(64))  # "P1-P6", "P5", ...
    started_at: Mapped[datetime] = mapped_column(DateTime)
    duration_s: Mapped[int] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16))  # done / failed / partial
    artifacts_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(String(512))


class NvlTraceability(Base):
    """Truy vết NVL — mỗi mã: xuất SX → vào TP / khoá BTP / khoá TP / còn lại."""

    __tablename__ = "nvl_traceability"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    material: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(String(512))
    uom: Mapped[str | None] = mapped_column(String(16))
    xuat_sx: Mapped[float] = mapped_column(Float, default=0.0)
    cho_xuat_khau: Mapped[float] = mapped_column(Float, default=0.0)
    trong_tp_ton: Mapped[float] = mapped_column(Float, default=0.0)
    trong_btp_ton: Mapped[float] = mapped_column(Float, default=0.0)
    giai_trinh: Mapped[float] = mapped_column(Float, default=0.0)
    con_lai: Mapped[float] = mapped_column(Float, default=0.0)
    pct_giai_trinh: Mapped[float] = mapped_column(Float, default=0.0)


class RiskFinding(Base):
    """Rủi ro nghiệp vụ tìm thấy ở Phase 3-4 — pain point bán hàng."""

    __tablename__ = "risk_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(16))  # R01, R02, ...
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16))  # high/medium/low
    category: Mapped[str] = mapped_column(String(64))  # truy_thu / phan_loai / dinh_muc / ...
    materials_count: Mapped[int] = mapped_column(Integer, default=0)
    quantity_impact: Mapped[float | None] = mapped_column(Float)
    money_impact_vnd: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)
    if_ignored: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    regulation_ref: Mapped[str | None] = mapped_column(String(128))


class ProcessLog(Base):
    """Nhật ký xử lý — read-only, kể chuyện ai làm gì lúc nào."""

    __tablename__ = "process_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    actor: Mapped[str] = mapped_column(String(128))
    actor_role: Mapped[str | None] = mapped_column(String(64))
    phase_no: Mapped[int | None] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text)


class ValidationResult(Base):
    """Phase 6 — 9 test validate cuối."""

    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    test_code: Mapped[str] = mapped_column(String(16))
    test_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16))  # pass/fail
    expected: Mapped[str | None] = mapped_column(String(255))
    actual: Mapped[str | None] = mapped_column(String(255))
    delta_pct: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)

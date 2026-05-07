"""Excel exporters cho Mẫu 15/15a/16 — chuẩn TT 39/2018.

- Mẫu 15 + 15a: dùng template Mau_BCQT_template.xlsx (header công ty, tiêu đề, cột chuẩn).
  Insert data rows vào giữa header và footer hướng dẫn.
- Mẫu 16: build fresh per Phụ lục II TT 39/2018 vì không có template.
"""

from __future__ import annotations

import io
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.models import Company, Mau15aRow, Mau15Row, Mau16Row

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates_xlsx" / "Mau_BCQT_template.xlsx"

# Common styles
_HEADER_FONT = Font(name="Times New Roman", size=11, bold=True)
_TITLE_FONT = Font(name="Times New Roman", size=13, bold=True)
_BODY_FONT = Font(name="Times New Roman", size=10)
_THIN = Side(border_style="thin", color="333333")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_RIGHT = Alignment(horizontal="right", vertical="center")


def _fill_company_header_15(ws, company: Company, kind: str = "M15") -> None:
    """Điền tên công ty / địa chỉ / MST vào header (chỗ trống của template)."""
    period = "Kỳ báo cáo: Từ ngày 01/01/2025 đến ngày 31/12/2025"
    if kind == "M15":
        ws.cell(3, 2).value = f"Công ty: {company.name}"
        ws.cell(4, 2).value = f"Địa chỉ: {company.province or '—'}"
        ws.cell(5, 2).value = f"Mã số thuế: {company.tax_code or '—'}"
        ws.cell(7, 2).value = period
    else:  # M15a
        ws.cell(4, 1).value = f"Công ty: {company.name}"
        ws.cell(5, 1).value = f"Địa chỉ: {company.province or '—'}"
        ws.cell(6, 1).value = f"Mã số thuế: {company.tax_code or '—'}"
        ws.cell(16, 1).value = period


def build_mau15_xlsx(company: Company, rows: Iterable[Mau15Row]) -> io.BytesIO:
    """Mẫu 15/BCQT-NVL/GSQL — dựa template, insert data rows vào row 12+."""
    wb = openpyxl.load_workbook(TEMPLATE_PATH)
    if "Mau 15a" in wb.sheetnames:
        del wb["Mau 15a"]
    ws = wb["Mau 15"]
    _fill_company_header_15(ws, company, "M15")

    rows_list = list(rows)
    n = len(rows_list)

    # Insert N empty rows tại row 12 (đẩy footer xuống)
    if n > 0:
        ws.insert_rows(12, n)

    # Write data
    for i, r in enumerate(rows_list, start=1):
        rr = 11 + i  # bắt đầu từ row 12
        ws.cell(rr, 2).value = i  # STT
        ws.cell(rr, 3).value = r.material  # Mã nội bộ
        # col 4 (mã HQ) — không có data
        ws.cell(rr, 5).value = r.description  # Tên kế toán
        # col 6 (tên HQ) — không có data
        ws.cell(rr, 7).value = r.uom  # ĐVT kế toán
        # col 8 (ĐVT HQ) — không có data
        ws.cell(rr, 9).value = float(r.ton_dau_ky)
        ws.cell(rr, 10).value = float(r.nhap_trong_ky)  # nhập E11/E15 (đa số case)
        # col 11-14 (chi tiết nhập từ nguồn khác) — không có data tách
        ws.cell(rr, 15).value = float(r.nhap_trong_ky)  # tổng nhập
        # col 16 (tái xuất) — không có data
        # col 17 (chuyển MĐSD) — không có data
        ws.cell(rr, 18).value = float(r.xuat_san_xuat)  # xuất kho SX từ đơn lĩnh liệu
        # col 19 (xuất SX khác) — không có data
        ws.cell(rr, 20).value = float(r.xuat_san_xuat)  # tổng xuất SX
        ws.cell(rr, 21).value = float(r.xuat_khac)  # xuất khác
        ws.cell(rr, 22).value = float(r.ton_cuoi_ky)  # tồn cuối kỳ lý thuyết
        # col 23-24 (tồn thực tế / kiểm kê) — không có data
        # col 25 (ghi chú) — để trống

        # Style
        for col in (2, 9, 10, 15, 18, 20, 21, 22):
            ws.cell(rr, col).alignment = _RIGHT
        ws.cell(rr, 3).alignment = _LEFT
        ws.cell(rr, 5).alignment = _LEFT
        for col in range(2, 26):
            ws.cell(rr, col).font = _BODY_FONT

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_mau15a_xlsx(company: Company, rows: Iterable[Mau15aRow]) -> io.BytesIO:
    """Mẫu 15a/BCQT-SP/GSQL — dựa template, data rows từ row 22+."""
    wb = openpyxl.load_workbook(TEMPLATE_PATH)
    if "Mau 15" in wb.sheetnames:
        del wb["Mau 15"]
    ws = wb["Mau 15a"]
    _fill_company_header_15(ws, company, "M15a")

    rows_list = list(rows)
    n = len(rows_list)
    if n > 0:
        ws.insert_rows(22, n)

    for i, r in enumerate(rows_list, start=1):
        rr = 21 + i  # bắt đầu row 22
        ws.cell(rr, 1).value = i  # STT
        ws.cell(rr, 2).value = r.material  # Mã SP XK
        ws.cell(rr, 4).value = r.description  # Tên SP XK
        ws.cell(rr, 6).value = r.uom  # ĐVT
        ws.cell(rr, 8).value = float(r.ton_dau_ky)
        ws.cell(rr, 9).value = float(r.nhap_kho)  # tổng nhập
        # col 10-12: detail breakdown nhập — không tách
        ws.cell(rr, 13).value = float(r.nhap_kho)  # tổng nhập
        # col 14: chuyển MĐSD — không có data
        ws.cell(rr, 15).value = float(r.xuat_khau)
        ws.cell(rr, 16).value = float(r.xuat_khac)
        ws.cell(rr, 17).value = float(r.ton_cuoi_ky)
        # col 18 (kiểm kê) — không có
        # col 19 (ghi chú) — trống

        for col in (1, 8, 9, 13, 15, 16, 17):
            ws.cell(rr, col).alignment = _RIGHT
        ws.cell(rr, 2).alignment = _LEFT
        ws.cell(rr, 4).alignment = _LEFT
        for col in range(1, 20):
            ws.cell(rr, col).font = _BODY_FONT

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def build_mau16_xlsx(company: Company, rows: Iterable[Mau16Row]) -> io.BytesIO:
    """Mẫu 16/ĐMTT/GSQL — build fresh theo Phụ lục II TT 39/2018."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Mau 16"

    # Column widths
    widths = [5, 18, 30, 12, 18, 30, 12, 14, 12]  # cols 1-9
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Header rows
    ws.cell(1, 1).value = "Mẫu số 16/ĐMTT/GSQL"
    ws.cell(1, 1).font = Font(name="Times New Roman", size=11, bold=True, italic=True)
    ws.cell(1, 1).alignment = Alignment(horizontal="left")

    ws.merge_cells("A2:I2")
    ws.cell(2, 1).value = "(Ban hành kèm theo Phụ lục II Thông tư 39/2018/TT-BTC)"
    ws.cell(2, 1).font = Font(name="Times New Roman", size=10, italic=True)
    ws.cell(2, 1).alignment = Alignment(horizontal="right")

    # Company info
    ws.cell(4, 1).value = f"Công ty: {company.name}"
    ws.cell(5, 1).value = f"Địa chỉ: {company.province or '—'}"
    ws.cell(6, 1).value = f"Mã số thuế: {company.tax_code or '—'}"
    for r in (4, 5, 6):
        ws.cell(r, 1).font = _HEADER_FONT

    # CHXHCN VN (right block)
    ws.merge_cells("E4:I4")
    ws.cell(4, 5).value = "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    ws.cell(4, 5).font = Font(name="Times New Roman", size=11, bold=True)
    ws.cell(4, 5).alignment = Alignment(horizontal="center")

    ws.merge_cells("E5:I5")
    ws.cell(5, 5).value = "Độc lập - Tự do - Hạnh phúc"
    ws.cell(5, 5).font = Font(name="Times New Roman", size=11, bold=True, italic=True)
    ws.cell(5, 5).alignment = Alignment(horizontal="center")

    # Title
    ws.merge_cells("A8:I8")
    ws.cell(8, 1).value = "BÁO CÁO ĐỊNH MỨC THỰC TẾ ĐỂ GIA CÔNG, SẢN XUẤT SẢN PHẨM XUẤT KHẨU"
    ws.cell(8, 1).font = _TITLE_FONT
    ws.cell(8, 1).alignment = _CENTER

    ws.merge_cells("A9:I9")
    ws.cell(9, 1).value = "Kỳ báo cáo: Từ ngày 01/01/2025 đến ngày 31/12/2025"
    ws.cell(9, 1).font = Font(name="Times New Roman", size=11, italic=True)
    ws.cell(9, 1).alignment = _CENTER

    # Column headers (row 11-12)
    headers = [
        ("STT", "(1)"),
        ("Mã sản phẩm xuất khẩu", "(2)"),
        ("Tên sản phẩm xuất khẩu", "(3)"),
        ("Đơn vị tính sản phẩm", "(4)"),
        ("Mã nguyên liệu, vật tư", "(5)"),
        ("Tên nguyên liệu, vật tư", "(6)"),
        ("Đơn vị tính NL, VT", "(7)"),
        ("Định mức thực tế", "(8)"),
        ("Ghi chú (X = nội địa, KXDĐM)", "(9)"),
    ]
    for i, (label, num) in enumerate(headers, 1):
        ws.cell(11, i).value = label
        ws.cell(11, i).font = _HEADER_FONT
        ws.cell(11, i).alignment = _CENTER
        ws.cell(11, i).fill = PatternFill("solid", fgColor="E8F0E8")
        ws.cell(11, i).border = _BORDER
        ws.cell(12, i).value = num
        ws.cell(12, i).font = Font(name="Times New Roman", size=10, italic=True)
        ws.cell(12, i).alignment = _CENTER
        ws.cell(12, i).border = _BORDER
    ws.row_dimensions[11].height = 36

    # Data rows
    last_tp = None
    stt = 0
    for i, r in enumerate(rows, start=1):
        rr = 12 + i
        # Display STT only on first NVL of each TP để dễ đọc
        if r.tp_code != last_tp:
            stt += 1
            ws.cell(rr, 1).value = stt
            ws.cell(rr, 2).value = r.tp_code
            ws.cell(rr, 3).value = r.tp_name
            ws.cell(rr, 4).value = r.tp_uom
            last_tp = r.tp_code
        ws.cell(rr, 5).value = r.nvl_code
        ws.cell(rr, 6).value = r.nvl_name
        ws.cell(rr, 7).value = r.nvl_uom
        ws.cell(rr, 8).value = float(r.norm) if r.norm else 0.0
        ws.cell(rr, 8).number_format = "0.000000"
        ws.cell(rr, 9).value = r.note or ""

        for col in range(1, 10):
            cell = ws.cell(rr, col)
            cell.font = _BODY_FONT
            cell.border = _BORDER
            if col in (1, 4, 7, 8):
                cell.alignment = Alignment(horizontal="center", vertical="top")
            elif col == 8:
                cell.alignment = _RIGHT
            else:
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # Signature block
    sig_row = 14 + (i if last_tp else 0)
    ws.cell(sig_row, 6).value = f"…………., ngày {datetime.now().strftime('%d/%m/%Y')}"
    ws.cell(sig_row, 6).font = Font(name="Times New Roman", size=10, italic=True)
    ws.cell(sig_row, 6).alignment = Alignment(horizontal="center")
    ws.cell(sig_row + 1, 6).value = "Người đại diện theo pháp luật của tổ chức, cá nhân"
    ws.cell(sig_row + 1, 6).font = Font(name="Times New Roman", size=11, bold=True)
    ws.cell(sig_row + 1, 6).alignment = Alignment(horizontal="center")
    ws.cell(sig_row + 2, 6).value = "(Ký, ghi rõ họ tên, đóng dấu)"
    ws.cell(sig_row + 2, 6).font = Font(name="Times New Roman", size=10, italic=True)
    ws.cell(sig_row + 2, 6).alignment = Alignment(horizontal="center")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

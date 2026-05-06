"""Helpers cho format số liệu Việt Nam và các tiện ích Jinja."""

from __future__ import annotations

import json
import math
from typing import Any


def fmt_num(v: Any, decimals: int | None = None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and math.isnan(v):
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if decimals is None:
        if abs(n - round(n)) < 1e-6:
            return f"{n:,.0f}".replace(",", ".")
        decimals = 2
    return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: Any, decimals: int = 1) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.{decimals}f}%"
    except Exception:
        return str(v)


def fmt_money(v: Any, currency: str = "VND") -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
    except Exception:
        return str(v)
    if currency == "VND":
        return f"{fmt_num(n, 0)} ₫"
    if currency == "USD":
        return f"${fmt_num(n, 2)}"
    return f"{fmt_num(n)} {currency}"


def parse_metrics(s: str | None) -> dict:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}


_VI_STATUS = {
    "done": "Hoàn tất",
    "running": "Đang chạy",
    "pending": "Chờ chạy",
    "failed": "Thất bại",
    "partial": "Một phần",
    "pass": "Đạt",
    "fail": "Không đạt",
}

_VI_SEVERITY = {
    "critical": "Nghiêm trọng",
    "warning": "Cảnh báo",
    "warn": "Cảnh báo",
    "info": "Thông tin",
    "high": "Cao",
    "medium": "Trung bình",
    "low": "Thấp",
}

_VI_DIRECTION = {
    "import": "Nhập",
    "export": "Xuất",
}


def vi_status(v: Any) -> str:
    if v is None:
        return "—"
    s = str(v).strip().lower()
    return _VI_STATUS.get(s, str(v))


def vi_severity(v: Any) -> str:
    if v is None:
        return "—"
    s = str(v).strip().lower()
    return _VI_SEVERITY.get(s, str(v))


def vi_direction(v: Any) -> str:
    if v is None or v == "":
        return "—"
    s = str(v).strip().lower()
    return _VI_DIRECTION.get(s, str(v))

"""Trích đoạn văn bản pháp lý — hiển thị inline tooltip khi hover/click tag."""

from __future__ import annotations

EXCERPTS: dict[str, dict] = {
    "TT 38/2015 Đ55": {
        "title": "Điều 55 — Định mức thực tế để gia công, sản xuất hàng hoá xuất khẩu",
        "doc": "TT 38/2015/TT-BTC ngày 25/3/2015",
        "issuer": "Bộ Tài chính",
        "excerpt": (
            "1. Định mức thực tế để gia công, sản xuất sản phẩm xuất khẩu, gồm: "
            "a) Định mức sử dụng nguyên liệu là lượng nguyên liệu cần thiết, thực tế sử dụng để sản xuất một đơn vị sản phẩm; "
            "b) Định mức vật tư tiêu hao là lượng vật tư tiêu hao thực tế để sản xuất một đơn vị sản phẩm; "
            "c) Tỷ lệ hao hụt nguyên liệu hoặc vật tư là lượng nguyên liệu hoặc vật tư thực tế hao hụt bao gồm hao hụt tự nhiên, "
            "hao hụt do tạo thành phế liệu, phế phẩm tính theo tỷ lệ % so với định mức thực tế sản xuất."
        ),
    },
    "TT 39/2018 K35Đ1": {
        "title": "Khoản 35 Điều 1 — Sửa đổi, bổ sung Điều 55 TT 38/2015",
        "doc": "TT 39/2018/TT-BTC ngày 20/4/2018",
        "issuer": "Bộ Tài chính",
        "excerpt": (
            "Định mức thực tế là lượng nguyên liệu, vật tư thực tế đã sử dụng để gia công, sản xuất một đơn vị sản phẩm xuất khẩu "
            "do tổ chức, cá nhân tự xây dựng, lưu giữ, chịu trách nhiệm trước pháp luật. "
            "Trường hợp xác định lượng nguyên liệu, vật tư cụ thể cấu thành trong từng đơn vị sản phẩm là khó khăn, "
            "tổ chức cá nhân tự xây dựng định mức bình quân theo dây chuyền hoặc theo lô sản phẩm, "
            "đảm bảo tổng định mức từng nguyên liệu/vật tư thực tế sử dụng tương ứng với tổng số sản phẩm sản xuất ra."
        ),
    },
    "TT 121/2025": {
        "title": "Quy đổi hàng dở dang trong báo cáo quyết toán",
        "doc": "TT 121/2025/TT-BTC, hiệu lực 01/02/2026",
        "issuer": "Bộ Tài chính",
        "excerpt": (
            "Tổ chức, cá nhân phải có thuật toán quy đổi hàng dở dang (BTP, sản phẩm chưa hoàn thành) "
            "về nguyên liệu cấu thành tại thời điểm chốt báo cáo quyết toán. "
            "Thuật toán phải được xây dựng theo nguyên tắc nhất quán, lưu giữ tài liệu để giải trình khi cơ quan hải quan kiểm tra. "
            "(Văn bản này thay thế nội dung quy đổi tại TT 39/2018.)"
        ),
    },
    "PL II Mẫu 16": {
        "title": "Mẫu 16/ĐMTT/GSQL — Định mức thực tế",
        "doc": "Phụ lục II TT 39/2018",
        "issuer": "Bộ Tài chính",
        "excerpt": (
            "Cột (2)-(3): Mã và tên sản phẩm xuất khẩu, phải thống nhất với mã/tên đã khai trên tờ khai hải quan. "
            "Cột (5)-(6): Mã và tên nguyên liệu/vật tư bao gồm cả nhập khẩu và mua trong nước, "
            "phải thống nhất với mã NVL đã khai trên tờ khai hải quan. "
            "Cột (8): Định mức = Tổng NVL thực tế sử dụng ÷ Tổng sản phẩm thu được. "
            "Cột (9): NVL nội địa ghi 'X', NVL nhập khẩu để trống, vật tư không xác định được định mức ghi 'KXDĐM'."
        ),
    },
    "PL V Mẫu 15/15a": {
        "title": "Mẫu 15/BCQT-NVL và 15a/BCQT-SP",
        "doc": "Phụ lục V TT 39/2018",
        "issuer": "Bộ Tài chính",
        "excerpt": (
            "Mẫu 15: Báo cáo quyết toán nhập-xuất-tồn nguyên liệu, vật tư. "
            "Ghi chú: 'Bán thành phẩm được tạo ra từ nguyên liệu nhập khẩu chưa được thể hiện chi tiết tại biểu mẫu này, "
            "tổ chức cá nhân theo dõi, lưu giữ và giải trình khi cơ quan hải quan kiểm tra.' "
            "Mẫu 15a: Báo cáo quyết toán nhập-xuất-tồn thành phẩm xuất khẩu hoàn chỉnh — không khai BTP nội bộ."
        ),
    },
    "QĐ 1357/QĐ-TCHQ": {
        "title": "Bảng mã loại hình xuất khẩu, nhập khẩu",
        "doc": "QĐ 1357/QĐ-TCHQ ngày 18/5/2021",
        "issuer": "Tổng cục Hải quan",
        "excerpt": (
            "Bảng mã loại hình chính thức gồm 16 mã xuất khẩu (B11, B12, B13, E42, E54, E62, ...) "
            "và 24 mã nhập khẩu (A11, A12, A21, E11, E13, E15, G12, G13, ...) áp dụng cho khai báo VNACCS. "
            "Mỗi mã xác định loại hình giao dịch (kinh doanh, gia công, SXXK, DNCX, tạm nhập tái xuất, ...) "
            "và quy định về thuế áp dụng. Mã không có trong bảng → khai báo bị bác."
        ),
    },
    "CV 3304/TCHQ-GSQL": {
        "title": "Phân biệt CCDC và vật tư tiêu hao",
        "doc": "CV 3304/TCHQ-GSQL ngày 27/5/2019",
        "issuer": "Tổng cục Hải quan",
        "excerpt": (
            "Vật tư tiêu hao trong sản xuất hàng XK (sơn, dây hàn, hoá chất ...) nhập theo loại hình E11/E15 "
            "→ phải đưa vào báo cáo quyết toán Mẫu 15. "
            "Công cụ dụng cụ (CCDC) sử dụng nhiều lần, không cấu thành vào sản phẩm, nhập theo loại hình E13 "
            "→ KHÔNG đưa vào báo cáo quyết toán. "
            "Việc xác định CCDC vs vật tư tiêu hao căn cứ vào mã loại hình nhập + bản chất sử dụng thực tế."
        ),
    },
}


def get_excerpt(code: str) -> dict | None:
    return EXCERPTS.get(code)

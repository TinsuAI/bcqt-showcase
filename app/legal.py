"""Trích đoạn văn bản pháp lý — hiển thị inline tooltip khi hover/click tag.

Mỗi entry có 2 phần tách bạch để tránh rủi ro pháp lý:
- summary: tóm tắt nội dung (không phải nguyên văn — viết lại bằng tiếng Việt thường)
- interpretation: cách Trọng Tín áp dụng văn bản này vào pipeline (diễn giải nghiệp vụ)

Không trích nguyên văn vì chưa verify từng câu chữ với văn bản gốc của cơ quan ban hành.
Người đọc cần xem văn bản gốc để đối chiếu chính xác.
"""

from __future__ import annotations

EXCERPTS: dict[str, dict] = {
    "TT 38/2015 Đ55": {
        "title": "Điều 55 — Định mức thực tế để gia công, sản xuất hàng hoá xuất khẩu",
        "doc": "TT 38/2015/TT-BTC ngày 25/3/2015",
        "issuer": "Bộ Tài chính",
        "summary": (
            "Quy định về 3 thành phần của định mức thực tế: (a) định mức sử dụng nguyên liệu — "
            "lượng nguyên liệu thực tế cần để sản xuất một đơn vị sản phẩm; (b) định mức vật tư tiêu hao — "
            "lượng vật tư thực tế tiêu hao cho một đơn vị sản phẩm; (c) tỷ lệ hao hụt — "
            "lượng nguyên liệu/vật tư hao hụt thực tế (gồm hao hụt tự nhiên và hao hụt do tạo phế liệu, phế phẩm)."
        ),
        "interpretation": (
            "Pipeline tính cả 3 thành phần này từ dữ liệu MB51 thực tế: định mức = tổng tiêu hao ÷ tổng thành phẩm. "
            "Phần hao hụt + phế liệu được giải trình riêng trong sheet truy vết NVL."
        ),
    },
    "TT 39/2018 K35Đ1": {
        "title": "Khoản 35 Điều 1 — Sửa đổi Điều 55 TT 38/2015",
        "doc": "TT 39/2018/TT-BTC ngày 20/4/2018",
        "issuer": "Bộ Tài chính",
        "summary": (
            "Định mức thực tế là lượng nguyên liệu, vật tư đã sử dụng để sản xuất một đơn vị sản phẩm xuất khẩu, "
            "do tổ chức/cá nhân tự xây dựng, lưu giữ và chịu trách nhiệm trước pháp luật. "
            "Khi khó xác định lượng cụ thể cho từng đơn vị sản phẩm, có thể xây dựng định mức bình quân "
            "theo dây chuyền hoặc theo lô, đảm bảo tổng định mức tương ứng với tổng sản phẩm sản xuất ra."
        ),
        "interpretation": (
            "Pipeline áp dụng phương án định mức bình quân — tổng hợp toàn bộ lệnh sản xuất trong kỳ "
            "rồi tính bình quân theo từng cặp (NVL, thành phẩm). Đây là cách phù hợp khi sản xuất hàng loạt "
            "và đa dạng phiên bản."
        ),
    },
    "TT 121/2025": {
        "title": "Quy định về quy đổi hàng dở dang trong báo cáo quyết toán",
        "doc": "TT 121/2025/TT-BTC, hiệu lực 01/02/2026",
        "issuer": "Bộ Tài chính",
        "verified": False,
        "summary": (
            "Tổ chức, cá nhân phải có thuật toán quy đổi hàng dở dang (bán thành phẩm, sản phẩm chưa hoàn thành) "
            "về nguyên liệu cấu thành tại thời điểm chốt báo cáo quyết toán. "
            "Thuật toán phải nhất quán và lưu tài liệu để giải trình khi cơ quan hải quan kiểm tra."
        ),
        "interpretation": (
            "Pipeline đáp ứng yêu cầu này: BTP tồn cuối kỳ được quy đổi về NVL gốc qua hệ số định mức, "
            "ghi vào sheet truy vết. Thuật toán cùng tham số được lưu trong hồ sơ giải trình kèm báo cáo."
        ),
    },
    "PL II Mẫu 16": {
        "title": "Mẫu 16/ĐMTT/GSQL — Định mức thực tế",
        "doc": "Phụ lục II TT 39/2018",
        "issuer": "Bộ Tài chính",
        "summary": (
            "Cột (2)-(3): mã và tên sản phẩm xuất khẩu, phải thống nhất với mã/tên đã khai trên tờ khai hải quan. "
            "Cột (5)-(6): mã và tên nguyên liệu, vật tư (gồm cả nhập khẩu và mua trong nước), "
            "phải thống nhất với mã đã khai trên tờ khai hải quan. "
            "Cột (8): định mức = tổng nguyên liệu thực tế sử dụng ÷ tổng sản phẩm thu được. "
            "Cột (9): nguyên liệu nội địa ghi 'X', nguyên liệu nhập khẩu để trống, "
            "vật tư không xác định được định mức ghi 'KXDĐM'."
        ),
        "interpretation": (
            "Pipeline sinh đúng các cột này: tham chiếu chéo mã NVL với dữ liệu hải quan để gán cờ X/để trống/KXDĐM. "
            "Bán thành phẩm tự sản xuất không xuất hiện ở cột (5)-(6) — đã được đưa về NVL gốc trước khi đưa vào mẫu."
        ),
    },
    "PL V Mẫu 15/15a": {
        "title": "Mẫu 15/BCQT-NVL và 15a/BCQT-SP",
        "doc": "Phụ lục V TT 39/2018",
        "issuer": "Bộ Tài chính",
        "summary": (
            "Mẫu 15: báo cáo quyết toán nhập-xuất-tồn nguyên liệu, vật tư. "
            "Phụ lục có ghi chú: bán thành phẩm tạo ra từ nguyên liệu nhập khẩu chưa được thể hiện chi tiết "
            "tại biểu mẫu này, tổ chức/cá nhân theo dõi, lưu giữ và giải trình khi cơ quan hải quan kiểm tra. "
            "Mẫu 15a: báo cáo quyết toán nhập-xuất-tồn thành phẩm xuất khẩu hoàn chỉnh — không khai BTP nội bộ."
        ),
        "interpretation": (
            "Pipeline lưu chi tiết BTP tồn cuối kỳ + lượng NVL khoá trong BTP ở sheet riêng, "
            "kèm thuật toán quy đổi để cán bộ hải quan có thể đối chiếu khi yêu cầu giải trình."
        ),
    },
    "QĐ 1357/QĐ-TCHQ": {
        "title": "Bảng mã loại hình xuất khẩu, nhập khẩu",
        "doc": "QĐ 1357/QĐ-TCHQ ngày 18/5/2021",
        "issuer": "Tổng cục Hải quan",
        "summary": (
            "Ban hành bảng mã loại hình chính thức gồm 16 mã xuất khẩu (B11, B12, B13, E42, E54, E62, …) "
            "và 24 mã nhập khẩu (A11, A12, A21, E11, E13, E15, G12, G13, …) áp dụng cho khai báo hải quan. "
            "Mỗi mã xác định loại hình giao dịch (kinh doanh, gia công, sản xuất xuất khẩu, doanh nghiệp chế xuất, "
            "tạm nhập tái xuất, …) và hướng dẫn áp dụng kèm theo."
        ),
        "interpretation": (
            "Pipeline kiểm tra mọi tờ khai BCCT theo bảng này: mã loại hình lạ → cờ riêng để rà soát thay vì "
            "âm thầm bỏ qua. Mỗi loại hình quyết định cách xử lý ở Mẫu 15 (E11/E15 vào BCQT, E13 thường là CCDC)."
        ),
    },
    "CV 3304/TCHQ-GSQL": {
        "title": "Hướng dẫn phân biệt CCDC và vật tư tiêu hao",
        "doc": "CV 3304/TCHQ-GSQL ngày 27/5/2019",
        "issuer": "Tổng cục Hải quan",
        "summary": (
            "Hướng dẫn xác định công cụ dụng cụ (CCDC) so với vật tư tiêu hao trong sản xuất hàng xuất khẩu. "
            "CCDC thường được sử dụng nhiều lần, không cấu thành vào sản phẩm. "
            "Vật tư tiêu hao (sơn, dây hàn, hoá chất, …) bị hao hụt khi sản xuất hàng xuất khẩu. "
            "Việc xác định căn cứ vào mã loại hình nhập khẩu kết hợp với bản chất sử dụng thực tế."
        ),
        "interpretation": (
            "Pipeline phân loại theo cặp (mã loại hình nhập khẩu, hành vi MB51): "
            "vật tư nhập E11/E15 và có hành vi tiêu hao trong sản xuất → đưa vào Mẫu 15; "
            "CCDC nhập E13 và sử dụng nhiều lần → KHÔNG đưa vào Mẫu 15. "
            "Trường hợp ranh giới được cờ riêng để hỏi doanh nghiệp."
        ),
    },
}


def get_excerpt(code: str) -> dict | None:
    return EXCERPTS.get(code)

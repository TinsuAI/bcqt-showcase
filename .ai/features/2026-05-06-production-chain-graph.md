# Feature: Đồ thị dây chuyền sản xuất

## Scope

**Có làm:**
- Route mới `/c/{slug}/bom` — đồ thị BOM cho 1 mã TP (input mã TP → render).
- 2 chế độ xem:
  - **Trực tiếp (multi-level)**: TP → BTP → ... → NVL gốc theo BOM_Direct (35.636 cạnh thực, depth 2-4).
  - **Flatten**: TP ↔ NVL gốc trực tiếp (BOM_Flat 57.054 dòng) — Sankey-style cho thấy quantity flow.
- Search input + danh sách 8-10 TP đề xuất (TP có nhiều input nhất, từ data thật).
- Color-code theo level: TP root xanh đậm, BTP_SX cam (cycle nodes vàng), NVL xanh nhạt.
- Click 1 node → tooltip show: norm, consumed, produced, level.
- Highlight các mã trong cycle (44 mã thuộc 20 SCC).
- Pre-pick: nếu không có `?tp=` query, default vào MFW0512-39 (đã verify có 44 NVL gốc, đẹp để demo).

**KHÔNG làm:**
- Không render toàn bộ network 35K cạnh cùng lúc (overload, không đọc được).
- Không cho user edit BOM (read-only viewer).
- Không simulate "thêm BOM" hay "tính lại" (uncanny valley risk theo critic).
- Không export PDF (đã có Excel export ở pipeline gốc).

## Decisions

1. **Stack viz**: ECharts `graph` series (đã loaded sẵn ở base.html). Layout `force` cho non-trivial chains, `circular` cho TP có ít node. Không dùng D3 / Cytoscape.
2. **Data source**: pull `BOM_Direct` (35.636 dòng) + `BOM_Flat` (57.054 dòng) từ `HO_SO_GIAI_TRINH_v12.0.xlsx` vào DB. Thêm bảng `BomEdge` (general, không chỉ cycle) thay vì mở rộng `BomCycleEdge` — tách concern rõ.
3. **Depth limit**: hard cap 4 levels khi expand recursive. Nếu TP có >50 nodes ở depth 2, truncate và show counter "+N nữa" để tránh canvas bị quá tải.
4. **Cycle detection inline**: khi expand gặp node đã visit → mark là "cycle reference" (style đặc biệt, không expand tiếp). Tận dụng `bom_cycles` table có sẵn để mark trước.
5. **Default TP**: query `?tp=MFW0512-39` (cycle node, 44 NVL gốc). User có thể đổi qua input search hoặc chip suggestion.
6. **Mode toggle**: 2 tab `Trực tiếp / Flatten`. Trực tiếp = tree-like graph nhiều cấp. Flatten = bipartite (1 TP ở giữa + N NVL gốc xung quanh) — đơn giản hoá, tốt cho TP có chain sâu.
7. **Performance**: lưu BomEdge index trên `(company_id, product)` để query nhanh khi expand.

## Risks

- **TP rất "rộng" (200+ inputs trực tiếp)**: MGM1317-406 có 223 inputs L1. Render 223 nodes trên 1 canvas sẽ khó đọc. Mitigate: chỉ render top 30 theo norm giảm dần, có chip "xem thêm 193".
- **Cycle gây infinite loop**: 44 mã trong 20 SCC. Visited-set trong expand recursive xử lý được, nhưng phải kỹ.
- **TP không có trong data**: user gõ mã sai → cần graceful fallback ("không tìm thấy + suggestions").
- **BOM_Direct seed lớn (35K row)**: SQLite ok, nhưng tăng init time. Có thể giới hạn depth khi seed (chỉ pull cạnh có norm > 0.001) — verify cần thiết hay không.
- **Mobile**: graph 700px width không vừa mobile. Hiện đã có `max-width: 880px` hide rail. Graph cần `responsive: true` của ECharts.
- **Uncanny valley**: tránh nút "tính lại BOM" giả lập. Giữ thuần read-only viewer như critic đã review.

## Open Questions

- **TP search UX**: chỉ cho gõ mã chính xác hay autocomplete (htmx)? → mặc định gõ chính xác + chip suggestion. Autocomplete có thể là follow-up.
- **Show consumed/produced quantity ở edge label?** Hay chỉ norm? → norm gọn hơn, consumed/produced vào tooltip.
- **Có cần "trace ngược"** (input mã NVL → show TP nào dùng)? → đã có ở `/c/{slug}/trace`. Không cần lặp lại ở đây.
- **Có nên gộp với Phase 5 cycles page?** → giữ riêng. Cycles là 1 góc nhìn (chỉ 44 mã); BOM graph là toàn cảnh BOM (517 TP).

## Suggested next step

Implement direct. Effort ước ~1.5h:
1. (15') Model + seed BomEdge (full BOM_Direct + BOM_Flat).
2. (30') Route `/c/{slug}/bom` với 2 mode + expand recursive.
3. (45') Template + ECharts setup (graph layout + tooltip + theme-aware color).
4. (10') Sidebar link "Đồ thị BOM" trong section "Nghiệp vụ".

Smoke test: 5 TP đại diện (cycle, dual-role, deep chain, wide chain, simple).

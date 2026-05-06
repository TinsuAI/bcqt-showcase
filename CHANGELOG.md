# Changelog

Theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/) và [Semantic Versioning](https://semver.org/lang/vi/).

## [Unreleased]

## [0.1.0] - 2026-05-06

### Added
- Khởi tạo project: FastAPI + Jinja2 SSR + HTMX + ECharts + SQLAlchemy + SQLite.
- 12 bảng DB cho 6-phase BCQT pipeline (multi-tenant).
- Seed loader pull data anonymized từ Johnson v12.0.
- Trang công ty + 6 phase pages (P1 Clean → P6 Validate) + cycle visualizer.
- Trang truy vết NVL (`/c/{slug}/trace`) — vòng đời 1 mã.
- Trang phát hiện rủi ro (`/c/{slug}/risks`) — 7 risk pain → solution.
- Trang nhật ký xử lý (`/c/{slug}/log`) — 14 log read-only.
- Trang đồ thị BOM (`/c/{slug}/bom`) — đồ thị 517 TP × 11.6K nodes / 11.1K edges, search arbitrary mã.
- Trang lịch sử chạy (`/c/{slug}/runs`) — 11 lần chạy v0.9 → v12.0.
- Trang quy tắc xử lý (`/c/{slug}/rules`) — 7 file YAML read-only.
- Per-phase Input/Output blocks + last-run badge.
- Theme dark/light toggle.

[Unreleased]: https://github.com/TinsuAI/bcqt-showcase/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/TinsuAI/bcqt-showcase/releases/tag/v0.1.0

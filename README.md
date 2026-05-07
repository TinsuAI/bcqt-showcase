# BCQT Showcase

Demo Báo Cáo Quyết Toán Hải Quan — showcase pipeline 6 phase từ dữ liệu thô SAP/VNACCS đến mẫu 15/15a/16 nộp hải quan.

## Stack
- FastAPI + Jinja2 SSR + HTMX + Alpine.js
- SQLAlchemy 2.0 + Alembic, SQLite (dev) hoặc Postgres (prod)
- ECharts cho cycle graph và biểu đồ KPI
- Custom CSS design system (Manrope + IBM Plex Mono, emerald palette, dark mode)

## Quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env
python -m app.seed.load_demo
uvicorn app.main:app --reload --port 8080
```

Mở `http://localhost:8080`.

## Cấu trúc

```
app/
  main.py          FastAPI app + middleware + lifespan
  config.py        Settings từ .env
  db.py            SQLAlchemy engine/session
  models.py        12 bảng cho 6 phase
  routes/          Phase landing + drill-down
  templates/       Jinja2 SSR
  static/          CSS / JS / hình
  seed/            Loader: output pipeline thật → DB (anonymized)
data/              SQLite file
migrations/        Alembic
docs/              Design notes, page wireframes
```

## Data

Demo pull số liệu thật từ pipeline thật (anonymized: tên công ty đổi thành "Công ty FDI A", giữ nguyên số liệu). 2 công ty mock thêm vào để minh hoạ multi-tenant.

## License
Internal — Trọng Tín.

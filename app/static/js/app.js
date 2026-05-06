// Dark/light theme toggle, persisted to localStorage.
(() => {
    const KEY = "bcqt-theme";
    const initial = localStorage.getItem(KEY) || "dark";
    document.body.dataset.theme = initial;
    window.addEventListener("DOMContentLoaded", () => {
        const btn = document.getElementById("theme-toggle");
        if (!btn) return;
        const updateLabel = () => {
            btn.textContent = document.body.dataset.theme === "dark" ? "☀" : "☾";
        };
        updateLabel();
        btn.addEventListener("click", () => {
            const cur = document.body.dataset.theme;
            const next = cur === "dark" ? "light" : "dark";
            document.body.dataset.theme = next;
            localStorage.setItem(KEY, next);
            updateLabel();
            window.dispatchEvent(new CustomEvent("theme-changed", { detail: next }));
        });
    });
})();

// Sortable tables: any <table class="data sortable"> with <th data-sort="num|text"> becomes sortable.
(() => {
    const parseCell = (td, type) => {
        if (type === "num") {
            const txt = (td.textContent || "").replace(/[.\s]/g, "").replace(",", ".").replace(/[^\d.\-]/g, "");
            const n = parseFloat(txt);
            return isNaN(n) ? -Infinity : n;
        }
        return (td.textContent || "").trim().toLowerCase();
    };

    const sortTable = (table, colIdx, type, asc) => {
        const tbody = table.tBodies[0];
        if (!tbody) return;
        const rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort((a, b) => {
            const va = parseCell(a.cells[colIdx], type);
            const vb = parseCell(b.cells[colIdx], type);
            if (va < vb) return asc ? -1 : 1;
            if (va > vb) return asc ? 1 : -1;
            return 0;
        });
        rows.forEach(r => tbody.appendChild(r));
    };

    window.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll("table.data.sortable").forEach(table => {
            const headers = table.querySelectorAll("thead th[data-sort]");
            headers.forEach((th, idx) => {
                // Find actual column index (across all th in thead row)
                const allTh = Array.from(th.parentElement.children);
                const colIdx = allTh.indexOf(th);
                const type = th.dataset.sort;
                th.classList.add("sortable-col");
                th.addEventListener("click", () => {
                    const cur = th.dataset.dir || "";
                    const next = cur === "asc" ? "desc" : "asc";
                    headers.forEach(h => { h.dataset.dir = ""; h.classList.remove("sort-asc", "sort-desc"); });
                    th.dataset.dir = next;
                    th.classList.add(next === "asc" ? "sort-asc" : "sort-desc");
                    sortTable(table, colIdx, type, next === "asc");
                });
            });
        });
    });
})();

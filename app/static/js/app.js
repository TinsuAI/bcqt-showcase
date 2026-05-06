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

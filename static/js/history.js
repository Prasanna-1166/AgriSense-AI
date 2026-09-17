/* ==========================================================================
   CropWise V2 — history.js
   Prediction history list, view, and delete/clear actions.
   ========================================================================== */

const CropWiseHistory = {
  init() {
    document.getElementById("refreshHistoryBtn").addEventListener("click", () => this.load());
    document.getElementById("clearHistoryBtn").addEventListener("click", () => this.clearAll());

    document.querySelector('.nav-item[data-section="history"]').addEventListener("click", () => this.load());
  },

  async load() {
    const emptyEl = document.getElementById("historyEmpty");
    const listEl = document.getElementById("historyList");

    try {
      const res = await fetch("/api/history?limit=30");
      const data = await res.json();
      const predictions = data.predictions || [];

      if (predictions.length === 0) {
        emptyEl.classList.remove("hidden");
        listEl.innerHTML = "";
        return;
      }

      emptyEl.classList.add("hidden");
      listEl.innerHTML = predictions.map(p => this.renderItem(p)).join("");

      listEl.querySelectorAll(".history-delete-btn").forEach(btn => {
        btn.addEventListener("click", () => this.deleteItem(btn.dataset.id));
      });

    } catch (e) {
      listEl.innerHTML = `<p class="small-muted">Could not load history.</p>`;
    }
  },

  renderItem(p) {
    const date = p.timestamp ? new Date(p.timestamp).toLocaleString() : "Unknown time";
    const locationName = p.location && p.location.lat !== undefined
      ? `${p.location.lat.toFixed(3)}, ${p.location.lon.toFixed(3)}`
      : "Unknown location";

    return `
      <div class="history-item">
        <div class="history-item-main">
          <span class="history-item-crop">${p.recommended_crop ? this.capitalize(p.recommended_crop) : "—"}</span>
          <span class="history-item-meta">${date} · ${locationName} · ${p.mode || ""} mode</span>
        </div>
        <div class="history-item-stats">
          <span>${p.suitability_pct !== undefined && p.suitability_pct !== null ? p.suitability_pct + "%" : "—"}</span>
          <span>${p.estimated_yield !== undefined && p.estimated_yield !== null ? p.estimated_yield.toFixed(1) + " t/ha" : "—"}</span>
          <span>${p.data_quality || "—"}</span>
        </div>
        <button class="history-delete-btn" data-id="${p.id}" title="Delete">✕</button>
      </div>
    `;
  },

  async deleteItem(id) {
    if (!id) return;
    try {
      await fetch(`/api/history/${id}`, { method: "DELETE" });
      this.load();
    } catch (e) {
      CropWise.toast("Could not delete this entry.", "error");
    }
  },

  async clearAll() {
    if (!confirm("Clear all prediction history? This cannot be undone.")) return;
    try {
      await fetch("/api/history", { method: "DELETE" });
      this.load();
      CropWise.toast("History cleared.");
    } catch (e) {
      CropWise.toast("Could not clear history.", "error");
    }
  },

  capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  },
};

window.CropWiseHistory = CropWiseHistory;
document.addEventListener("DOMContentLoaded", () => CropWiseHistory.init());

/* ==========================================================================
   CropWise V2 — app.js
   Core application state, navigation, and shared utilities.
   ========================================================================== */

const CropWise = {
  state: {
    mode: "assisted",           // quick | assisted | expert (assisted is the default mode)
    selectedLocation: null,      // {lat, lon, name}
    lastPrediction: null,        // full response from /api/predict/*
    manualOverrides: {},         // user-entered feature values (assisted/expert)
  },

  FEATURE_META: {
    N: { label: "Nitrogen", unit: "kg/ha" },
    P: { label: "Phosphorus", unit: "kg/ha" },
    K: { label: "Potassium", unit: "kg/ha" },
    temperature: { label: "Temperature", unit: "°C" },
    humidity: { label: "Humidity", unit: "%" },
    ph: { label: "Soil pH", unit: "pH" },
    rainfall: { label: "Rainfall", unit: "mm/year" },
  },

  init() {
    this.bindNavigation();
    this.bindMobileMenu();
    this.bindModeTabs();
    this.checkModelHealth();
    this.loadModelInfo();
    if (window.CropWisePrediction) {
      window.CropWisePrediction.onModeChange(this.state.mode);
    }
  },

  async loadModelInfo() {
    const box = document.getElementById("modelInfoBox");
    if (!box) return;
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const meta = (data.models && data.models.metadata) || {};
      const cropMeta = meta.crop_model || {};
      const yieldMeta = meta.yield_model || {};

      box.innerHTML = `
        <p><strong>Crop model:</strong> ${cropMeta.type || "RandomForestClassifier"},
        trained on ${cropMeta.dataset_size || "—"} rows
        ${cropMeta.accuracy ? `(test accuracy ${(cropMeta.accuracy * 100).toFixed(1)}%)` : ""}.</p>
        <p><strong>Yield model:</strong> ${yieldMeta.type || "RandomForestRegressor"} —
        ${yieldMeta.notes || "synthetic/estimated model."}</p>
      `;
    } catch (e) {
      box.textContent = "Model information is currently unavailable.";
    }
  },

  bindNavigation() {
    document.querySelectorAll(".nav-item").forEach(btn => {
      btn.addEventListener("click", () => this.gotoSection(btn.dataset.section));
    });
    document.querySelectorAll("[data-goto]").forEach(btn => {
      btn.addEventListener("click", () => this.gotoSection(btn.dataset.goto));
    });
  },

  gotoSection(sectionId) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

    const page = document.getElementById(`page-${sectionId}`);
    const navBtn = document.querySelector(`.nav-item[data-section="${sectionId}"]`);
    if (page) page.classList.add("active");
    if (navBtn) navBtn.classList.add("active");

    // Close mobile sidebar on navigation
    document.getElementById("sidebar").classList.remove("open");

    // Lazy-init map when the location page becomes visible
    if (sectionId === "location" && window.CropWiseMap) {
      window.CropWiseMap.ensureInit();
    }
  },

  bindMobileMenu() {
    const btn = document.getElementById("mobileMenuBtn");
    const sidebar = document.getElementById("sidebar");
    if (btn) {
      btn.addEventListener("click", () => sidebar.classList.toggle("open"));
    }
  },

  bindModeTabs() {
    document.querySelectorAll(".mode-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".mode-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        this.state.mode = tab.dataset.mode;
        if (window.CropWisePrediction) {
          window.CropWisePrediction.onModeChange(this.state.mode);
        }
      });
    });
  },

  async checkModelHealth() {
    const dot = document.getElementById("modelStatusDot");
    const text = document.getElementById("modelStatusText");
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      if (data.status === "ok") {
        dot.className = "status-dot status-dot--ok";
        text.textContent = "Models ready";
      } else {
        dot.className = "status-dot status-dot--degraded";
        text.textContent = "Models not trained";
        this.toast("Prediction models aren't trained yet. See README for training steps.", "error");
      }
    } catch (e) {
      dot.className = "status-dot status-dot--degraded";
      text.textContent = "Server unreachable";
    }
  },

  toast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const el = document.createElement("div");
    el.className = `toast ${type === "error" ? "toast--error" : ""}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), 5000);
  },

  formatNumber(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) return "—";
    return Number(value).toFixed(decimals);
  },

  statusBadgeHtml(status) {
    const map = {
      retrieved: { label: "Retrieved", cls: "status-retrieved" },
      estimated: { label: "Estimated", cls: "status-estimated" },
      fallback: { label: "Default", cls: "status-fallback" },
      manual: { label: "Manual", cls: "status-manual" },
    };
    const info = map[status] || { label: status || "Unknown", cls: "status-fallback" };
    return `<span class="status-badge ${info.cls}">${info.label}</span>`;
  },

  confidenceClass(overall) {
    if (overall === "high") return "confidence-high";
    if (overall === "low") return "confidence-low";
    return "confidence-moderate";
  },
};

document.addEventListener("DOMContentLoaded", () => CropWise.init());

/* ==========================================================================
   AgriSense AI — current_farm.js
   "I have a farm/crop already" situational analysis flow.
   ========================================================================== */

const CropWiseCurrentFarm = {
  init() {
    document.getElementById("analyzeCurrentFarmBtn").addEventListener("click", () => this.analyze());
    document.querySelector('.nav-item[data-section="current-farm"]').addEventListener("click", () => this.refreshLocationDisplay());
  },

  refreshLocationDisplay() {
    const el = document.getElementById("cfLocationDisplay");
    const loc = CropWise.state.selectedLocation;
    if (loc) {
      el.textContent = `${loc.name || "Selected location"} (${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)})`;
    } else {
      el.textContent = "No location set yet — set one in Farm Location first.";
    }
  },

  async analyze() {
    const errorBox = document.getElementById("cfError");
    const statusEl = document.getElementById("cfAnalyzingStatus");
    errorBox.classList.add("hidden");

    const loc = CropWise.state.selectedLocation;
    const cropSelect = document.getElementById("currentCropSelect");
    const currentCrop = cropSelect.value;

    if (!loc) {
      errorBox.textContent = "Please set a farm location first (Farm Location page).";
      errorBox.classList.remove("hidden");
      return;
    }
    if (!currentCrop) {
      errorBox.textContent = "Please select your current crop.";
      errorBox.classList.remove("hidden");
      return;
    }

    statusEl.classList.remove("hidden");

    const payload = {
      lat: loc.lat,
      lon: loc.lon,
      current_crop: currentCrop,
      crop_stage: document.getElementById("cropStageInput").value.trim() || undefined,
      area_ha: parseFloat(document.getElementById("cfAreaInput").value) || 1.0,
      irrigation: document.getElementById("cfIrrigationSelect").value,
    };

    try {
      const res = await fetch("/api/farm/analyze-current", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      statusEl.classList.add("hidden");

      if (!res.ok && res.status !== 422) {
        errorBox.textContent = data.error || "Analysis failed. Please try again.";
        errorBox.classList.remove("hidden");
        return;
      }

      this.render(data);
    } catch (e) {
      statusEl.classList.add("hidden");
      errorBox.textContent = "Could not reach the server. Please check your connection and try again.";
      errorBox.classList.remove("hidden");
    }
  },

  render(data) {
    document.getElementById("cfResults").classList.remove("hidden");

    const statsEl = document.getElementById("cfStats");
    if (data.suitability_available && data.crop_analysis) {
      const c = data.crop_analysis;
      statsEl.innerHTML = `
        <div class="stat-card stat-card--accent">
          <span class="stat-label">Current Crop</span>
          <span class="stat-value">${c.icon} ${this.capitalize(c.crop)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Suitability (current conditions)</span>
          <span class="stat-value">${c.suitability_pct}%</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Estimated Yield</span>
          <span class="stat-value">${CropWise.formatNumber(c.predicted_yield_t_per_ha)} t/ha</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Farm Production</span>
          <span class="stat-value">${CropWise.formatNumber(c.predicted_total_production_t)} t</span>
        </div>
      `;
    } else {
      statsEl.innerHTML = `
        <div class="stat-card">
          <span class="stat-label">Current Crop</span>
          <span class="stat-value">${this.capitalize(data.current_crop)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Suitability</span>
          <span class="stat-value">Data unavailable</span>
        </div>
      `;
    }

    document.getElementById("cfMessage").textContent = data.message ||
      "Analysis based on current weather, soil, and your reported farm details.";

    const insightsEl = document.getElementById("cfInsights");
    insightsEl.innerHTML = (data.insights || []).map(insight => `
      <div class="insight-card insight-card--${insight.type}">
        <span class="insight-icon">${insight.icon}</span>
        <span>${insight.text}</span>
      </div>
    `).join("") || `<p class="small-muted">No insights available.</p>`;

    const risksEl = document.getElementById("cfRisks");
    risksEl.innerHTML = (data.risks || []).map(risk => window.CropWisePrediction.renderRiskItem(risk)).join("") ||
      `<p class="small-muted">No risk assessment available.</p>`;
  },

  capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  },
};

window.CropWiseCurrentFarm = CropWiseCurrentFarm;
document.addEventListener("DOMContentLoaded", () => CropWiseCurrentFarm.init());

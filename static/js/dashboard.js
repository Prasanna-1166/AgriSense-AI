/* ==========================================================================
   CropWise V2 — dashboard.js
   Renders the main dashboard summary from the latest prediction.
   ========================================================================== */

const CropWiseDashboard = {
  render(data) {
    document.getElementById("dashboardEmpty").classList.add("hidden");
    document.getElementById("dashboardContent").classList.remove("hidden");

    const top = data.top_crop;
    if (top) {
      document.getElementById("dashCrop").textContent = this.capitalize(top.crop);
      document.getElementById("dashCropIcon").textContent = top.icon;
      document.getElementById("dashSuitability").textContent = `${top.suitability_pct}%`;
      document.getElementById("dashYield").textContent = `${CropWise.formatNumber(top.predicted_yield_t_per_ha)} t/ha`;
      document.getElementById("dashProduction").textContent = `${CropWise.formatNumber(top.predicted_total_production_t)} t`;
    }

    const loc = data.location || {};
    document.getElementById("dashLocationName").textContent =
      (CropWise.state.selectedLocation && CropWise.state.selectedLocation.name) || "Selected farm location";
    document.getElementById("dashCoords").textContent =
      (loc.lat !== undefined) ? `${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)}` : "—";

    const dq = data.data_quality || {};
    const badge = document.getElementById("dashConfidenceBadge");
    badge.textContent = (dq.overall || "moderate").toUpperCase();
    badge.className = `confidence-badge ${CropWise.confidenceClass(dq.overall)}`;

    // Weather summary
    const climate = (data.environment_profile) || {};
    const weatherEl = document.getElementById("dashWeatherSummary");
    weatherEl.innerHTML = this.summaryRows([
      ["Temperature", climate.temperature, "°C"],
      ["Humidity", climate.humidity, "%"],
      ["Rainfall", climate.rainfall, "mm/yr"],
    ]);

    const soilEl = document.getElementById("dashSoilSummary");
    soilEl.innerHTML = this.summaryRows([
      ["Nitrogen (N)", climate.N, "kg/ha"],
      ["Phosphorus (P)", climate.P, "kg/ha"],
      ["Potassium (K)", climate.K, "kg/ha"],
      ["Soil pH", climate.ph, ""],
    ]);

    // Alternatives (skip #1, it's already the headline)
    const altEl = document.getElementById("dashAlternatives");
    const alternatives = (data.ranked_crops || []).slice(1, 4);
    altEl.innerHTML = alternatives.map(c => `
      <div class="alt-crop-row">
        <span class="alt-crop-name">${c.icon} ${this.capitalize(c.crop)}</span>
        <span class="alt-crop-pct">${c.suitability_pct}%</span>
      </div>
    `).join("") || `<p class="small-muted">No alternatives available.</p>`;
  },

  summaryRows(rows) {
    return rows.map(([label, item, unit]) => {
      const value = item && item.value !== undefined && item.value !== null
        ? `${CropWise.formatNumber(item.value, unit === "" ? 2 : 1)} ${unit}`
        : "—";
      return `
        <div class="summary-row">
          <span class="summary-row-label">${label}</span>
          <span class="summary-row-value">${value}</span>
        </div>
      `;
    }).join("");
  },

  capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  },
};

window.CropWiseDashboard = CropWiseDashboard;

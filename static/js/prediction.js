/* ==========================================================================
   CropWise V2 — prediction.js
   Drives the three prediction modes, manual field rendering, and the
   main "Analyze My Farm" flow.
   ========================================================================== */

const CropWisePrediction = {
  envProfile: null, // last-fetched environment profile for the selected location

  onModeChange(mode) {
    const card = document.getElementById("manualFieldsCard");
    const title = document.getElementById("manualFieldsTitle");
    const subtitle = document.getElementById("manualFieldsSubtitle");

    if (mode === "quick") {
      card.classList.add("hidden");
    } else if (mode === "assisted") {
      card.classList.remove("hidden");
      title.textContent = "Refine your values (optional)";
      subtitle.textContent = "Auto-filled where possible. Override anything you know more precisely.";
      this.renderManualFields(true);
    } else if (mode === "expert") {
      card.classList.remove("hidden");
      title.textContent = "Enter your soil test values";
      subtitle.textContent = "Expert mode requires all fields below for the highest input accuracy.";
      this.renderManualFields(false);
    }
  },

  async onLocationChanged(lat, lon) {
    if (CropWise.state.mode === "quick") return; // Quick mode doesn't need prefill display

    const grid = document.getElementById("manualFieldsGrid");
    grid.innerHTML = `<div class="small-muted">Fetching environmental data for this location…</div>`;

    try {
      const res = await fetch("/api/environment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lon }),
      });
      const data = await res.json();
      this.envProfile = data;
      this.renderManualFields(CropWise.state.mode === "assisted");
    } catch (e) {
      grid.innerHTML = `<div class="small-muted">Could not fetch environmental data. You can still enter values manually.</div>`;
    }
  },

  renderManualFields(prefill) {
    const grid = document.getElementById("manualFieldsGrid");
    grid.innerHTML = "";

    const featureOrder = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];

    featureOrder.forEach(feat => {
      const meta = CropWise.FEATURE_META[feat];
      const wrapper = document.createElement("div");
      wrapper.className = "source-field";

      let prefillValue = "";
      let statusBadge = "";
      if (prefill && this.envProfile) {
        const climateKeyMap = { temperature: "climate", humidity: "climate", rainfall: "climate" };
        let item = null;
        if (["N", "P", "K", "ph"].includes(feat)) {
          item = this.envProfile.soil ? this.envProfile.soil[feat] : null;
        } else {
          item = this.envProfile.climate ? this.envProfile.climate[feat] : null;
        }
        if (item && item.value !== null && item.value !== undefined) {
          prefillValue = item.value;
          statusBadge = CropWise.statusBadgeHtml(item.status) +
            `<span class="source-field-meta">${item.source || ""}</span>`;
        }
      }

      wrapper.innerHTML = `
        <div class="source-field-label">
          <span>${meta.label} (${meta.unit})</span>
          ${statusBadge}
        </div>
        <input type="number" step="0.01" id="field_${feat}" value="${prefillValue}" placeholder="Enter ${meta.label.toLowerCase()}">
      `;
      grid.appendChild(wrapper);
    });
  },

  gatherFarmInputs() {
    return {
      area_ha: parseFloat(document.getElementById("farmAreaInput").value) || 1.0,
      irrigation: document.getElementById("irrigationSelect").value,
      soil_type: document.getElementById("soilTypeInput").value.trim() || undefined,
      growing_season: document.getElementById("seasonInput").value.trim() || undefined,
      previous_crop: document.getElementById("prevCropInput").value.trim() || undefined,
    };
  },

  gatherManualFeatureValues() {
    const featureOrder = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
    const values = {};
    featureOrder.forEach(feat => {
      const input = document.getElementById(`field_${feat}`);
      if (input && input.value !== "") {
        values[feat] = parseFloat(input.value);
      }
    });
    return values;
  },

  async runPrediction() {
    const errorBox = document.getElementById("predictionError");
    const statusEl = document.getElementById("analyzingStatus");
    errorBox.classList.add("hidden");

    const loc = CropWise.state.selectedLocation;
    const mode = CropWise.state.mode;

    if (mode !== "expert" && (!loc || loc.lat === undefined)) {
      errorBox.textContent = "Please select a farm location first.";
      errorBox.classList.remove("hidden");
      return;
    }

    statusEl.classList.remove("hidden");

    const farmInputs = this.gatherFarmInputs();
    let endpoint = "/api/predict/quick";
    let payload = { lat: loc ? loc.lat : undefined, lon: loc ? loc.lon : undefined, ...farmInputs };

    if (mode === "assisted") {
      endpoint = "/api/predict/assisted";
      const soilOverrides = window.CropWiseSoil ? window.CropWiseSoil.gatherModelRelevantSoilOverrides() : {};
      payload = { ...payload, ...this.gatherManualFeatureValues(), ...soilOverrides };
    } else if (mode === "expert") {
      endpoint = "/api/predict/expert";
      const soilOverrides = window.CropWiseSoil ? window.CropWiseSoil.gatherModelRelevantSoilOverrides() : {};
      const manualValues = { ...this.gatherManualFeatureValues(), ...soilOverrides };
      const featureOrder = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"];
      const missing = featureOrder.filter(f => manualValues[f] === undefined);
      if (missing.length > 0) {
        statusEl.classList.add("hidden");
        errorBox.textContent = `Expert mode requires all fields. Missing: ${missing.join(", ")}`;
        errorBox.classList.remove("hidden");
        return;
      }
      payload = { ...payload, ...manualValues };
      if (loc) { payload.lat = loc.lat; payload.lon = loc.lon; }
    }

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      statusEl.classList.add("hidden");

      if (!res.ok) {
        errorBox.textContent = data.error || "Prediction failed. Please try again.";
        errorBox.classList.remove("hidden");
        return;
      }

      CropWise.state.lastPrediction = data;
      this.saveToHistory(data);
      this.renderAllSections(data);
      CropWise.toast("Analysis complete — check your Dashboard.");
      CropWise.gotoSection("dashboard");

    } catch (e) {
      statusEl.classList.add("hidden");
      errorBox.textContent = "Could not reach the server. Please check your connection and try again.";
      errorBox.classList.remove("hidden");
    }
  },

  async saveToHistory(prediction) {
    try {
      await fetch("/api/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prediction),
      });
    } catch (e) { /* history save is best-effort */ }
  },

  renderAllSections(data) {
    if (window.CropWiseDashboard) window.CropWiseDashboard.render(data);
    this.renderSoilEnvironment(data);
    this.renderRecommendation(data);
    this.renderYield(data);
    if (window.CropWiseCharts) {
      window.CropWiseCharts.renderComparison(data);
    }
    this.renderInsights(data);
    if (window.CropWiseWeather && data.location) {
      window.CropWiseWeather.load(data.location.lat, data.location.lon);
    }
  },

  renderSoilEnvironment(data) {
    document.getElementById("soilEnvEmpty").classList.add("hidden");
    document.getElementById("soilEnvContent").classList.remove("hidden");

    const profile = data.environment_profile || {};
    const soilKeys = ["N", "P", "K", "ph"];
    const climateKeys = ["temperature", "humidity", "rainfall"];

    const soilList = document.getElementById("soilProfileList");
    soilList.innerHTML = soilKeys.map(k => this.renderProfileParam(k, profile[k])).join("");

    const climateList = document.getElementById("climateProfileList");
    let climateHtml = climateKeys.map(k => this.renderProfileParam(k, profile[k])).join("");
    if (data.elevation) {
      climateHtml += this.renderProfileParam("elevation", data.elevation, "Elevation", "m");
    }
    climateList.innerHTML = climateHtml;

    document.getElementById("soilTypeEstimate").textContent =
      data.soil_type_estimate || "Not available for this location.";
  },

  renderProfileParam(key, item, labelOverride, unitOverride) {
    if (!item) return "";
    const meta = CropWise.FEATURE_META[key] || {};
    const label = labelOverride || meta.label || key;
    const unit = unitOverride || item.unit || meta.unit || "";
    return `
      <div class="profile-param">
        <div>
          <div class="profile-param-name">${label}</div>
          <div class="profile-param-source">${item.source || ""}</div>
        </div>
        <div class="profile-param-value">
          <strong>${CropWise.formatNumber(item.value, key === "ph" ? 2 : 1)}</strong> ${unit}<br>
          ${CropWise.statusBadgeHtml(item.status)}
        </div>
      </div>
    `;
  },

  renderRecommendation(data) {
    document.getElementById("recEmpty").classList.add("hidden");
    document.getElementById("recContent").classList.remove("hidden");

    const list = document.getElementById("rankedCropList");
    list.innerHTML = (data.ranked_crops || []).map((crop, idx) => `
      <div class="ranked-crop-card ${idx === 0 ? 'ranked-crop-card--top' : ''}">
        <div class="ranked-crop-head">
          <div class="ranked-crop-title">
            <span>${crop.icon}</span>
            <span>${this.capitalize(crop.crop)}</span>
            <span class="ranked-crop-rank">#${idx + 1}</span>
          </div>
          <div class="ranked-crop-suit">${crop.suitability_pct}%</div>
        </div>
        <div class="suit-bar-track"><div class="suit-bar-fill" style="width:${crop.suitability_pct}%"></div></div>
        <div class="ranked-crop-meta">
          <span>Yield: <strong>${CropWise.formatNumber(crop.predicted_yield_t_per_ha)} t/ha</strong></span>
          <span>Total production: <strong>${CropWise.formatNumber(crop.predicted_total_production_t)} t</strong></span>
          <span>Range: <strong>${CropWise.formatNumber(crop.yield_range_t_per_ha.low)}–${CropWise.formatNumber(crop.yield_range_t_per_ha.high)} t/ha</strong></span>
        </div>
      </div>
    `).join("");

    // Why this crop (top crop only)
    const top = data.top_crop;
    const whyEl = document.getElementById("whyThisCrop");
    if (top && top.explanation) {
      const checklistHtml = top.explanation.checklist.map(item => {
        const cls = item.ok === true ? "ok" : item.ok === false ? "bad" : "borderline";
        const icon = item.ok === true ? "✓" : item.ok === false ? "✕" : "◐";
        return `<div class="checklist-item checklist-item--${cls}"><span class="checklist-icon">${icon}</span><span>${item.text}</span></div>`;
      }).join("");

      let limitingHtml = "";
      if (top.explanation.limiting_factor) {
        limitingHtml = `<div class="limiting-factor">⚠ ${top.explanation.limiting_factor.text}</div>`;
      }

      whyEl.innerHTML = `<p class="small-muted">Why CropWise recommends ${this.capitalize(top.crop)}:</p>${checklistHtml}${limitingHtml}`;
    } else {
      whyEl.innerHTML = `<p class="small-muted">No explanation available.</p>`;
    }

    // Feature importance
    const fiEl = document.getElementById("featureImportanceChart");
    fiEl.innerHTML = (data.feature_importance || []).map(fi => `
      <div class="fi-row">
        <div class="fi-label">${fi.label}</div>
        <div class="fi-bar-track"><div class="fi-bar-fill" style="width:${fi.importance_pct}%"></div></div>
        <div class="fi-pct">${fi.importance_pct}%</div>
      </div>
    `).join("");
  },

  renderYield(data) {
    document.getElementById("yieldEmpty").classList.add("hidden");
    document.getElementById("yieldContent").classList.remove("hidden");

    const top = data.top_crop;
    if (!top) return;

    document.getElementById("yieldCrop").textContent = `${top.icon} ${this.capitalize(top.crop)}`;
    document.getElementById("yieldValue").textContent = `${CropWise.formatNumber(top.predicted_yield_t_per_ha)} t/ha`;
    document.getElementById("yieldArea").textContent = `${CropWise.formatNumber(data.farm.area_ha, 2)} ha`;
    document.getElementById("yieldTotal").textContent = `${CropWise.formatNumber(top.predicted_total_production_t)} t`;

    // Yield range bar
    const rangeEl = document.getElementById("yieldRangeBar");
    const low = top.yield_range_t_per_ha.low;
    const high = top.yield_range_t_per_ha.high;
    const mid = top.predicted_yield_t_per_ha;
    const maxScale = high * 1.3 || 1;
    const lowPct = (low / maxScale) * 100;
    const highPct = (high / maxScale) * 100;
    const midPct = (mid / maxScale) * 100;

    rangeEl.innerHTML = `
      <div class="yield-range-track"></div>
      <div class="yield-range-fill" style="left:${lowPct}%; width:${highPct - lowPct}%"></div>
      <div class="yield-range-marker" style="left:${midPct}%"></div>
      <div class="yield-range-labels">
        <span>${CropWise.formatNumber(low)} t/ha</span>
        <span>Estimate: ${CropWise.formatNumber(mid)} t/ha</span>
        <span>${CropWise.formatNumber(high)} t/ha</span>
      </div>
    `;

    const water = data.water_requirement || {};
    document.getElementById("irrigationEffect").textContent = water.adequacy ||
      "Irrigation effect information not available for this prediction.";
  },

  renderInsights(data) {
    document.getElementById("insightsEmpty").classList.add("hidden");
    document.getElementById("insightsContent").classList.remove("hidden");

    const list = document.getElementById("insightsList");
    list.innerHTML = (data.insights || []).map(insight => `
      <div class="insight-card insight-card--${insight.type}">
        <span class="insight-icon">${insight.icon}</span>
        <span>${insight.text}</span>
      </div>
    `).join("") || `<p class="small-muted">No insights available.</p>`;

    const riskList = document.getElementById("riskList");
    if (riskList) {
      riskList.innerHTML = (data.risks || []).map(risk => this.renderRiskItem(risk)).join("") ||
        `<p class="small-muted">No risk assessment available.</p>`;
    }
  },

  renderRiskItem(risk) {
    const levelClass = {
      "Low": "risk-low", "Moderate": "risk-moderate", "High": "risk-high",
      "Data unavailable": "risk-unknown"
    }[risk.level] || "risk-unknown";
    const categoryLabel = risk.category.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    return `
      <div class="risk-item ${levelClass}">
        <div class="risk-item-head">
          <span class="risk-category">${categoryLabel}</span>
          <span class="risk-level-badge">${risk.level}</span>
        </div>
        <p class="risk-explanation">${risk.explanation}</p>
        ${risk.rule ? `<p class="risk-rule">Rule: <code>${risk.rule}</code></p>` : ""}
      </div>
    `;
  },

  capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  },
};

window.CropWisePrediction = CropWisePrediction;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("runPredictionBtn").addEventListener("click", () => CropWisePrediction.runPrediction());
});

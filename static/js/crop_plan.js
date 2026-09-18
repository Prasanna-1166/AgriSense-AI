/* ==========================================================================
   AgriSense AI — crop_plan.js
   Crop Plan & Economics: seed/planting-material requirement, crop
   duration, fertilizer guidance, plant protection guidance, and a
   transparent (honestly-sourced) cost breakdown for the top
   recommended crop. Fetched from a dedicated backend endpoint
   (/api/crop-plan/<crop_id>) - kept separate from the ML prediction
   response on purpose (see docs/architecture.md).
   ========================================================================== */

const CropWiseCropPlan = {
  planStatusBadge(status) {
    const map = {
      VERIFIED_SOURCE: { label: "Verified source", cls: "status-retrieved" },
      SOURCE_ESTIMATE: { label: "Source estimate", cls: "status-estimated" },
      UNAVAILABLE: { label: "Unavailable", cls: "status-fallback" },
    };
    const info = map[status] || { label: status || "Unknown", cls: "status-fallback" };
    return `<span class="status-badge ${info.cls}">${info.label}</span>`;
  },

  sourceLine(source) {
    if (!source) return "";
    const bits = [source.org, source.title].filter(Boolean).join(" — ");
    const year = source.year ? ` (${source.year})` : "";
    if (source.url) {
      return `<a href="${source.url}" target="_blank" rel="noopener">${bits}${year}</a>`;
    }
    return `${bits}${year}`;
  },

  async loadForTopCrop(data) {
    const top = data && data.top_crop;
    if (!top) return;
    const areaHa = (data.farm && data.farm.area_ha) || 1.0;
    await this.load(top.crop, areaHa);
  },

  async load(cropId, areaHa) {
    document.getElementById("cropPlanEmpty").classList.add("hidden");
    document.getElementById("cropPlanContent").classList.add("hidden");
    document.getElementById("cropPlanLoading").classList.remove("hidden");

    try {
      const res = await fetch(`/api/crop-plan/${encodeURIComponent(cropId)}?area_ha=${encodeURIComponent(areaHa)}`);
      const plan = await res.json();
      document.getElementById("cropPlanLoading").classList.add("hidden");

      if (!res.ok) {
        document.getElementById("cropPlanEmpty").classList.remove("hidden");
        return;
      }
      this.render(plan);
    } catch (e) {
      document.getElementById("cropPlanLoading").classList.add("hidden");
      document.getElementById("cropPlanEmpty").classList.remove("hidden");
    }
  },

  render(plan) {
    document.getElementById("cropPlanContent").classList.remove("hidden");
    const SOURCED_STATUSES_TOP = ["VERIFIED_SOURCE", "SOURCE_ESTIMATE"];

    document.getElementById("cropPlanTitle").textContent = plan.display_name || CropWisePrediction.capitalize(plan.crop);
    document.getElementById("cropPlanRegionScope").textContent = plan.region_scope
      ? `Region scope: ${plan.region_scope}${plan.last_verified ? " · Last verified: " + plan.last_verified : ""}`
      : "Region scope: not specified for this crop's data.";

    const mlNoteEl = document.getElementById("cropPlanMlNote");
    if (plan.ml_support_note) {
      mlNoteEl.textContent = `⚠ ML recommendation unavailable for this crop: ${plan.ml_support_note} The agronomic reference information below is shown independently of any ML prediction.`;
    } else {
      mlNoteEl.textContent = "";
    }

    // Duration
    const durEl = document.getElementById("cropPlanDuration");
    const dur = plan.duration || {};
    if (dur.status === "VERIFIED_SOURCE") {
      durEl.innerHTML = `
        <p><strong>${dur.min_days}–${dur.max_days} days</strong> ${this.planStatusBadge(dur.status)}</p>
        <p class="small-muted">${dur.description || ""}</p>
        <p class="small-muted">Source: ${this.sourceLine(dur.source)}</p>
      `;
    } else {
      durEl.innerHTML = `<p>${this.planStatusBadge("UNAVAILABLE")}</p><p class="small-muted">${dur.note || "Not available."}</p>`;
    }

    // Seed / planting material
    const seedEl = document.getElementById("cropPlanSeed");
    const pm = plan.planting_material || {};
    if (SOURCED_STATUSES_TOP.includes(pm.status)) {
      seedEl.innerHTML = `
        <p><strong>${CropWise.formatNumber(pm.quantity_per_ha, 1)} ${pm.unit}/ha</strong> ${this.planStatusBadge(pm.status)}</p>
        ${pm.quantity_for_farm !== undefined ? `<p>For your farm (${CropWise.formatNumber(pm.farm_area_ha, 2)} ha): <strong>${CropWise.formatNumber(pm.quantity_for_farm, 1)} ${pm.unit}</strong></p>` : ""}
        ${pm.spacing ? `<p class="small-muted">Spacing: ${pm.spacing}</p>` : ""}
        ${pm.quantity_range ? `<p class="small-muted">${pm.quantity_range}</p>` : ""}
        ${pm.notes ? `<p class="small-muted">${pm.notes}</p>` : ""}
        <p class="small-muted">Source: ${this.sourceLine(pm.source)}</p>
      `;
    } else {
      seedEl.innerHTML = `<p>${this.planStatusBadge("UNAVAILABLE")}</p><p class="small-muted">${pm.note || "Not available."}</p>`;
    }

    // Fertilizers
    const fertNoteEl = document.getElementById("cropPlanFertilizerNote");
    fertNoteEl.textContent = plan.fertilizer_note || "";
    const fertEl = document.getElementById("cropPlanFertilizers");
    const ferts = plan.fertilizers;
    const SOURCED_STATUSES = SOURCED_STATUSES_TOP;
    if (Array.isArray(ferts) && ferts.length > 0) {
      fertEl.innerHTML = ferts.map(f => {
        const hasPerHa = f.quantity_per_ha !== null && f.quantity_per_ha !== undefined;
        const hasPerPlant = f.quantity_per_plant !== null && f.quantity_per_plant !== undefined;
        if (!SOURCED_STATUSES.includes(f.status) || (!hasPerHa && !hasPerPlant)) {
          return `
            <div class="profile-param">
              <div><div class="profile-param-name">${f.nutrient || f.name || "—"}</div></div>
              <div class="profile-param-value">${this.planStatusBadge("UNAVAILABLE")}</div>
            </div>
            ${f.notes ? `<p class="small-muted">${f.notes}</p>` : ""}
          `;
        }
        const valueHtml = hasPerHa
          ? `<strong>${CropWise.formatNumber(f.quantity_per_ha, 1)} ${f.unit || ""}</strong>
             ${f.quantity_for_farm !== undefined ? `<br>${CropWise.formatNumber(f.quantity_for_farm, 1)} for farm` : ""}`
          : `<strong>${CropWise.formatNumber(f.quantity_per_plant, 2)} ${f.unit_per_plant || ""}</strong>`;
        return `
          <div class="profile-param">
            <div>
              <div class="profile-param-name">${f.nutrient || f.name}</div>
              <div class="profile-param-source">${f.stage || ""}${f.purpose ? " — " + f.purpose : ""}</div>
            </div>
            <div class="profile-param-value">
              ${valueHtml}
              <br>${this.planStatusBadge(f.status)}
            </div>
          </div>
          ${f.notes ? `<p class="small-muted">${f.notes}</p>` : ""}
        `;
      }).join("") + `<p class="small-muted">Source: ${this.sourceLine(ferts[0].source)}</p>`;
    } else {
      fertEl.innerHTML = `<p>${this.planStatusBadge("UNAVAILABLE")}</p><p class="small-muted">No fertilizer recommendation on file for this crop.</p>`;
    }

    // Plant protection
    document.getElementById("cropPlanPPDisclaimer").textContent = plan.plant_protection_disclaimer || "";
    const ppEl = document.getElementById("cropPlanPlantProtection");
    const pp = plan.plant_protection;
    if (Array.isArray(pp) && pp.length > 0) {
      ppEl.innerHTML = pp.map(p => `
        <div class="risk-item risk-low">
          <div class="risk-item-head">
            <span class="risk-category">${p.target}</span>
            ${this.planStatusBadge(p.status)}
          </div>
          <p class="risk-explanation">${p.management || ""}</p>
          ${p.active_ingredient ? `<p class="small-muted">Active ingredient: ${p.active_ingredient}${p.rate ? " @ " + p.rate : ""}</p>` : ""}
          ${p.stage ? `<p class="small-muted">Stage: ${p.stage}</p>` : ""}
          <p class="small-muted">Source: ${this.sourceLine(p.source)}</p>
        </div>
      `).join("");
    } else {
      const note = (pp && pp.note) || "Plant-protection recommendation unavailable from verified sources.";
      ppEl.innerHTML = `<p>${this.planStatusBadge("UNAVAILABLE")}</p><p class="small-muted">${note}</p>`;
    }

    // Economics
    const econ = plan.economics || {};
    const survey = econ.surveyed_total;
    const summaryEl = document.getElementById("cropPlanCostSummary");

    if (survey) {
      summaryEl.innerHTML = `
        <div class="stat-card">
          <span class="stat-label">Status</span>
          <span class="stat-value" style="font-size:1rem;">Reported survey cost ${this.planStatusBadge("VERIFIED_SOURCE")}</span>
        </div>
        <div class="stat-card stat-card--accent">
          <span class="stat-label">Cost per hectare</span>
          <span class="stat-value">₹${CropWise.formatNumber(survey.total_per_ha, 0)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Farm area</span>
          <span class="stat-value">${CropWise.formatNumber(survey.area_ha, 2)} ha</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Estimated cost for farm</span>
          <span class="stat-value">₹${CropWise.formatNumber(survey.total_for_farm, 0)}</span>
        </div>
      `;
      const breakdownHtml = (survey.breakdown_pct && survey.breakdown_pct.length > 0)
        ? survey.breakdown_pct.map(b => `
            <div class="profile-param">
              <div><div class="profile-param-name">${b.component}</div></div>
              <div class="profile-param-value">${b.pct_of_total}% of total</div>
            </div>
          `).join("")
        : "";
      document.getElementById("cropPlanCostTable").innerHTML = `
        <p class="small-muted"><strong>${survey.cost_concept || ""}</strong></p>
        <p class="small-muted">Region: ${survey.region || "—"} · Year: ${survey.year || "—"}</p>
        ${breakdownHtml}
        <p class="small-muted">Source: ${this.sourceLine(survey.source)}</p>
      `;
      document.getElementById("cropPlanCostNote").textContent = survey.notes || "";
    } else {
      summaryEl.innerHTML = `
        <div class="stat-card">
          <span class="stat-label">Status</span>
          <span class="stat-value" style="font-size:1rem;">${econ.coverage_label || "—"}</span>
        </div>
        <div class="stat-card stat-card--accent">
          <span class="stat-label">Cost per hectare</span>
          <span class="stat-value">${econ.total_per_ha !== null && econ.total_per_ha !== undefined ? "₹" + CropWise.formatNumber(econ.total_per_ha, 0) : "—"}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Farm area</span>
          <span class="stat-value">${CropWise.formatNumber(econ.area_ha, 2)} ha</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Estimated cost for farm</span>
          <span class="stat-value">${econ.total_for_farm !== null && econ.total_for_farm !== undefined ? "₹" + CropWise.formatNumber(econ.total_for_farm, 0) : "—"}</span>
        </div>
      `;

      const tableEl = document.getElementById("cropPlanCostTable");
      if (Array.isArray(econ.components) && econ.components.length > 0) {
        tableEl.innerHTML = econ.components.map(c => `
          <div class="profile-param">
            <div>
              <div class="profile-param-name">${c.name}</div>
              <div class="profile-param-source">${CropWise.formatNumber(c.quantity_per_ha, 1)} ${c.unit || ""} / ha</div>
            </div>
            <div class="profile-param-value">
              ${c.cost_per_ha !== null && c.cost_per_ha !== undefined ? `<strong>₹${CropWise.formatNumber(c.cost_per_ha, 0)}/ha</strong>` : this.planStatusBadge("UNAVAILABLE")}
            </div>
          </div>
        `).join("");
      } else {
        tableEl.innerHTML = `<p class="small-muted">No cost components on file for this crop yet.</p>`;
      }
      document.getElementById("cropPlanCostNote").textContent = econ.note || "";
    }

    // Sources
    const sourcesEl = document.getElementById("cropPlanSources");
    if (Array.isArray(plan.sources) && plan.sources.length > 0) {
      sourcesEl.innerHTML = `<ul>${plan.sources.map(s => `<li>${this.sourceLine(s)}</li>`).join("")}</ul>`;
    } else {
      sourcesEl.innerHTML = `<p class="small-muted">No sources on file for this crop yet.</p>`;
    }

    document.getElementById("cropPlanDisclaimer").innerHTML =
      `<strong>Reference information, not a guarantee.</strong> ${plan.disclaimer || ""}`;
  },
};

window.CropWiseCropPlan = CropWiseCropPlan;

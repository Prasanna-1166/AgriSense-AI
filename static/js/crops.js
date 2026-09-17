/* ==========================================================================
   AgriSense AI — crops.js
   Crop Directory: shows every crop the system knows about, honestly
   labeling which have validated model coverage and which don't.
   ========================================================================== */

const CropWiseCrops = {
  allCrops: [],
  currentFilter: "all",

  init() {
    document.querySelector('.nav-item[data-section="crop-directory"]').addEventListener("click", () => this.load());
    document.querySelectorAll(".crop-filter").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".crop-filter").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentFilter = btn.dataset.filter;
        this.render();
      });
    });
    this.loadForCurrentFarmSelect();
  },

  async load() {
    if (this.allCrops.length > 0) { this.render(); return; }
    try {
      const res = await fetch("/api/crops");
      const data = await res.json();
      this.allCrops = data.crops || [];
      this.render();
    } catch (e) {
      document.getElementById("cropDirectoryGrid").innerHTML = `<p class="small-muted">Could not load crop directory.</p>`;
    }
  },

  render() {
    const grid = document.getElementById("cropDirectoryGrid");
    let crops = this.allCrops;
    if (this.currentFilter === "supported") crops = crops.filter(c => c.supported_for_recommendation);
    if (this.currentFilter === "unsupported") crops = crops.filter(c => !c.supported_for_recommendation);

    grid.innerHTML = crops.map(c => {
      if (c.supported_for_recommendation) {
        return `
          <div class="crop-directory-card crop-directory-card--supported">
            <div class="crop-directory-head">
              <strong>${c.display_name}</strong>
              <span class="status-badge status-retrieved">${c.data_availability}</span>
            </div>
            <p class="small-muted">${c.category} · ${c.observation_count_est} in training data</p>
            <p class="small-muted">Source: ${c.source}</p>
          </div>
        `;
      }
      return `
        <div class="crop-directory-card crop-directory-card--unsupported">
          <div class="crop-directory-head">
            <strong>${c.display_name}</strong>
            <span class="status-badge status-fallback">Data unavailable</span>
          </div>
          <p class="small-muted">${c.reason || ""}</p>
          <p class="small-muted">${c.real_world_data_note || ""}</p>
        </div>
      `;
    }).join("") || `<p class="small-muted">No crops match this filter.</p>`;
  },

  async loadForCurrentFarmSelect() {
    try {
      const res = await fetch("/api/crops");
      const data = await res.json();
      const select = document.getElementById("currentCropSelect");
      if (!select) return;
      select.innerHTML = `<option value="">Select your current crop…</option>` +
        (data.crops || []).map(c =>
          `<option value="${c.crop_id}" data-supported="${c.supported_for_recommendation}">${c.display_name}${c.supported_for_recommendation ? "" : " (data unavailable)"}</option>`
        ).join("");

      select.addEventListener("change", () => {
        const opt = select.options[select.selectedIndex];
        const warning = document.getElementById("currentCropWarning");
        if (opt && opt.dataset.supported === "false") {
          warning.textContent = "⚠ This crop has no validated data coverage in this system. Weather and soil information will still be shown, but no suitability or yield estimate will be generated.";
        } else {
          warning.textContent = "";
        }
      });
    } catch (e) { /* select stays at default */ }
  },
};

window.CropWiseCrops = CropWiseCrops;
document.addEventListener("DOMContentLoaded", () => CropWiseCrops.init());

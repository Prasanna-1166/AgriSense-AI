/* ==========================================================================
   AgriSense AI — soil.js
   Manual Soil Health Card entry + soil report upload/extraction.
   Extracted values are NEVER auto-trusted — always shown for confirmation.
   ========================================================================== */

const CropWiseSoil = {
  SHC_PARAMS: {
    ph: { label: "pH", unit: "" },
    ec: { label: "EC", unit: "dS/m" },
    organic_carbon: { label: "Organic Carbon", unit: "%" },
    N: { label: "Nitrogen (N)", unit: "kg/ha" },
    P: { label: "Phosphorus (P)", unit: "kg/ha" },
    K: { label: "Potassium (K)", unit: "kg/ha" },
    sulphur: { label: "Sulphur (S)", unit: "ppm" },
    zinc: { label: "Zinc (Zn)", unit: "ppm" },
    iron: { label: "Iron (Fe)", unit: "ppm" },
    manganese: { label: "Manganese (Mn)", unit: "ppm" },
    copper: { label: "Copper (Cu)", unit: "ppm" },
    boron: { label: "Boron (B)", unit: "ppm" },
  },

  manualValues: {}, // confirmed soil values (from manual entry OR confirmed extraction)

  init() {
    this.renderManualFields();
    document.querySelectorAll("[data-soil-tab]").forEach(tab => {
      tab.addEventListener("click", () => this.switchTab(tab.dataset.soilTab));
    });
    document.getElementById("soilUploadBtn").addEventListener("click", () => this.uploadAndExtract());
  },

  switchTab(tab) {
    document.querySelectorAll("[data-soil-tab]").forEach(t => t.classList.remove("active"));
    document.querySelector(`[data-soil-tab="${tab}"]`).classList.add("active");
    document.getElementById("soilManualPanel").classList.toggle("hidden", tab !== "manual");
    document.getElementById("soilUploadPanel").classList.toggle("hidden", tab !== "upload");
  },

  renderManualFields() {
    const grid = document.getElementById("soilManualPanel");
    grid.innerHTML = Object.entries(this.SHC_PARAMS).map(([key, meta]) => `
      <div class="field">
        <label for="shc_${key}">${meta.label}${meta.unit ? ` (${meta.unit})` : ""}</label>
        <input type="number" step="0.01" id="shc_${key}" placeholder="Optional">
      </div>
    `).join("");
  },

  gatherManualSoilValues() {
    const values = {};
    Object.keys(this.SHC_PARAMS).forEach(key => {
      const input = document.getElementById(`shc_${key}`);
      if (input && input.value !== "") {
        values[key] = parseFloat(input.value);
      }
    });
    return values;
  },

  /** Maps Soil Health Card fields onto the 4 fields the ML model actually uses (N, P, K, pH). */
  gatherModelRelevantSoilOverrides() {
    const shc = this.gatherManualSoilValues();
    const overrides = {};
    if (shc.N !== undefined) overrides.N = shc.N;
    if (shc.P !== undefined) overrides.P = shc.P;
    if (shc.K !== undefined) overrides.K = shc.K;
    if (shc.ph !== undefined) overrides.ph = shc.ph;
    return overrides;
  },

  async uploadAndExtract() {
    const fileInput = document.getElementById("soilFileInput");
    const resultEl = document.getElementById("soilExtractResult");

    if (!fileInput.files || fileInput.files.length === 0) {
      resultEl.textContent = "Please choose a file first.";
      return;
    }

    resultEl.textContent = "Extracting…";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const res = await fetch("/api/soil/extract", { method: "POST", body: formData });
      const data = await res.json();

      if (!data.success) {
        resultEl.textContent = data.message || "Extraction failed. Please enter values manually.";
        this.switchTab("manual");
        return;
      }

      // Extraction succeeded - show extracted values for CONFIRMATION,
      // never auto-applied.
      let html = `<p>${data.message}</p><div class="field-grid">`;
      Object.entries(data.extracted).forEach(([key, item]) => {
        const meta = this.SHC_PARAMS[key] || { label: key, unit: item.unit };
        html += `
          <div class="source-field">
            <div class="source-field-label"><span>${meta.label}</span>${CropWise.statusBadgeHtml("estimated")}</div>
            <input type="number" step="0.01" id="extract_${key}" value="${item.value}">
          </div>
        `;
      });
      html += `</div><button class="btn btn-primary" id="confirmExtractedBtn" style="margin-top:10px;">Confirm these values</button>`;
      resultEl.innerHTML = html;

      document.getElementById("confirmExtractedBtn").addEventListener("click", () => {
        Object.keys(data.extracted).forEach(key => {
          const el = document.getElementById(`extract_${key}`);
          if (el) {
            const manualEl = document.getElementById(`shc_${key}`);
            if (manualEl) manualEl.value = el.value;
          }
        });
        this.switchTab("manual");
        CropWise.toast("Extracted values confirmed and copied into manual entry.");
      });

    } catch (e) {
      resultEl.textContent = "Could not reach the extraction service. Please enter values manually.";
      this.switchTab("manual");
    }
  },
};

window.CropWiseSoil = CropWiseSoil;
document.addEventListener("DOMContentLoaded", () => CropWiseSoil.init());

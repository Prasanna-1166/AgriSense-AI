/* ==========================================================================
   AgriSense AI — farm.js
   Optional "My Farm" profile: save/load/delete, purely local, no auth.
   ========================================================================== */

const CropWiseFarm = {
  init() {
    document.querySelector('.nav-item[data-section="my-farm"]').addEventListener("click", () => this.load());
    document.getElementById("saveFarmProfileBtn").addEventListener("click", () => this.save());
    document.getElementById("deleteFarmProfileBtn").addEventListener("click", () => this.delete());
  },

  async load() {
    const display = document.getElementById("myFarmDisplay");
    try {
      const res = await fetch("/api/farm/profile");
      const data = await res.json();
      if (!data.exists) {
        display.innerHTML = `<p class="small-muted">No saved farm profile yet.</p>`;
        return;
      }
      const p = data.profile;
      display.innerHTML = `
        <div class="summary-list">
          ${p.location ? `<div class="summary-row"><span class="summary-row-label">Location</span><span class="summary-row-value">${p.location.lat?.toFixed(4)}, ${p.location.lon?.toFixed(4)}</span></div>` : ""}
          ${p.state ? `<div class="summary-row"><span class="summary-row-label">State</span><span class="summary-row-value">${p.state}</span></div>` : ""}
          ${p.district ? `<div class="summary-row"><span class="summary-row-label">District</span><span class="summary-row-value">${p.district}</span></div>` : ""}
          ${p.area_ha ? `<div class="summary-row"><span class="summary-row-label">Farm area</span><span class="summary-row-value">${p.area_ha} ha</span></div>` : ""}
          ${p.irrigation ? `<div class="summary-row"><span class="summary-row-label">Irrigation</span><span class="summary-row-value">${p.irrigation}</span></div>` : ""}
          ${p.current_crop ? `<div class="summary-row"><span class="summary-row-label">Current crop</span><span class="summary-row-value">${p.current_crop}</span></div>` : ""}
        </div>
      `;
    } catch (e) {
      display.innerHTML = `<p class="small-muted">Could not load farm profile.</p>`;
    }
  },

  async save() {
    const loc = CropWise.state.selectedLocation;
    const profile = {
      location: loc ? { lat: loc.lat, lon: loc.lon } : undefined,
      area_ha: parseFloat(document.getElementById("farmAreaInput")?.value) || undefined,
      irrigation: document.getElementById("irrigationSelect")?.value,
      current_crop: document.getElementById("currentCropSelect")?.value || undefined,
    };

    try {
      const res = await fetch("/api/farm/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        CropWise.toast("Farm profile saved.");
        this.load();
      } else {
        CropWise.toast("Could not save farm profile.", "error");
      }
    } catch (e) {
      CropWise.toast("Could not save farm profile.", "error");
    }
  },

  async delete() {
    if (!confirm("Delete your saved farm profile?")) return;
    try {
      await fetch("/api/farm/profile", { method: "DELETE" });
      this.load();
      CropWise.toast("Farm profile deleted.");
    } catch (e) {
      CropWise.toast("Could not delete farm profile.", "error");
    }
  },
};

window.CropWiseFarm = CropWiseFarm;
document.addEventListener("DOMContentLoaded", () => CropWiseFarm.init());

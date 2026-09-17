/* ==========================================================================
   AgriSense AI — geography.js
   State/district manual fallback and GPS location confirmation flow.
   ========================================================================== */

const CropWiseGeography = {
  statesLoaded: false,

  init() {
    this.loadStates();
    document.getElementById("stateSelect").addEventListener("change", (e) => this.onStateChange(e.target.value));
    document.getElementById("districtSelect").addEventListener("change", (e) => this.onDistrictChange(e.target.value));
  },

  async loadStates() {
    try {
      const res = await fetch("/api/location/states");
      const data = await res.json();
      const select = document.getElementById("stateSelect");
      select.innerHTML = `<option value="">Select state…</option>` +
        data.states.map(s => `<option value="${s}">${s}</option>`).join("");
      this.statesLoaded = true;
    } catch (e) {
      CropWise.toast("Could not load state list.", "error");
    }
  },

  async onStateChange(state) {
    const districtSelect = document.getElementById("districtSelect");
    if (!state) {
      districtSelect.innerHTML = `<option value="">Select district…</option>`;
      return;
    }
    try {
      const res = await fetch(`/api/location/districts?state=${encodeURIComponent(state)}`);
      const data = await res.json();
      if (data.districts && data.districts.length > 0) {
        districtSelect.innerHTML = `<option value="">Select district…</option>` +
          data.districts.map(d => `<option value="${d}">${d}</option>`).join("");
      } else {
        districtSelect.innerHTML = `<option value="">No district list maintained — using state only</option>`;
        // For states without a maintained district list, use a rough
        // approximate location via geocoding search on the state name.
        this.approximateLocationFromName(state);
      }
    } catch (e) {
      CropWise.toast("Could not load district list.", "error");
    }
  },

  async onDistrictChange(district) {
    const state = document.getElementById("stateSelect").value;
    if (!district || !state) return;
    this.approximateLocationFromName(`${district}, ${state}, India`);
  },

  async approximateLocationFromName(query) {
    try {
      const res = await fetch(`/api/location/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        const r = data.results[0];
        window.CropWiseMap.setLocation(r.lat, r.lon, r.display_name);
      } else {
        CropWise.toast("Could not resolve that state/district to coordinates. Try search or coordinates instead.", "error");
      }
    } catch (e) {
      CropWise.toast("Location search is currently unavailable.", "error");
    }
  },

  async confirmGpsLocation(lat, lon) {
    const box = document.getElementById("locationConfirmBox");
    const text = document.getElementById("locationConfirmText");
    box.classList.remove("hidden");
    text.textContent = "Resolving your location…";

    try {
      const res = await fetch(`/api/location/resolve?lat=${lat}&lon=${lon}`);
      const data = await res.json();
      if (data.resolved) {
        text.textContent = data.confirmation_prompt;
        document.getElementById("confirmLocationYes").onclick = () => {
          box.classList.add("hidden");
          CropWise.toast(`Location confirmed: ${data.district || ""}, ${data.state || ""}`.trim());
        };
        document.getElementById("confirmLocationNo").onclick = () => {
          box.classList.add("hidden");
          CropWise.gotoSection("location");
          document.getElementById("stateSelect").focus();
        };
      } else {
        text.textContent = data.error || "Could not resolve your location. Please select your state and district manually.";
        document.getElementById("confirmLocationYes").classList.add("hidden");
      }
    } catch (e) {
      box.classList.add("hidden");
    }
  },
};

window.CropWiseGeography = CropWiseGeography;
document.addEventListener("DOMContentLoaded", () => CropWiseGeography.init());

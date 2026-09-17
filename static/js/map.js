/* ==========================================================================
   CropWise V2 — map.js
   Leaflet map, location search, current-location, and coordinate entry.
   ========================================================================== */

const CropWiseMap = {
  map: null,
  marker: null,
  initialized: false,

  ensureInit() {
    if (this.initialized) {
      // Map container may have been hidden; refresh sizing
      setTimeout(() => this.map && this.map.invalidateSize(), 50);
      return;
    }
    this.initMap();
    this.bindControls();
    this.initialized = true;
  },

  initMap() {
    this.map = L.map("locationMap", { zoomControl: true }).setView([20.5937, 78.9629], 5); // Default: India view
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(this.map);

    this.map.on("click", (e) => {
      this.setLocation(e.latlng.lat, e.latlng.lng, null);
    });
  },

  bindControls() {
    document.getElementById("locationSearchBtn").addEventListener("click", () => this.doSearch());
    document.getElementById("locationSearchInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter") this.doSearch();
    });
    document.getElementById("useCurrentLocationBtn").addEventListener("click", () => this.useCurrentLocation());
    document.getElementById("useCoordsBtn").addEventListener("click", () => {
      const lat = parseFloat(document.getElementById("latInput").value);
      const lon = parseFloat(document.getElementById("lonInput").value);
      if (isNaN(lat) || isNaN(lon)) {
        CropWise.toast("Please enter valid latitude and longitude.", "error");
        return;
      }
      this.setLocation(lat, lon, null);
    });
  },

  async doSearch() {
    const query = document.getElementById("locationSearchInput").value.trim();
    const resultsEl = document.getElementById("locationSearchResults");
    if (!query) return;

    resultsEl.innerHTML = `<div class="small-muted">Searching…</div>`;

    try {
      const res = await fetch(`/api/location/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();

      if (data.error && (!data.results || data.results.length === 0)) {
        resultsEl.innerHTML = `<div class="small-muted">${data.error}</div>`;
        return;
      }

      resultsEl.innerHTML = "";
      data.results.forEach(r => {
        const btn = document.createElement("button");
        btn.className = "search-result-item";
        btn.textContent = r.display_name;
        btn.addEventListener("click", () => {
          this.setLocation(r.lat, r.lon, r.display_name);
          resultsEl.innerHTML = "";
          document.getElementById("locationSearchInput").value = r.display_name;
        });
        resultsEl.appendChild(btn);
      });
    } catch (e) {
      resultsEl.innerHTML = `<div class="small-muted">Search unavailable right now.</div>`;
    }
  },

  useCurrentLocation() {
    if (!navigator.geolocation) {
      CropWise.toast("Geolocation is not supported by your browser.", "error");
      return;
    }
    CropWise.toast("Requesting your location…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.setLocation(pos.coords.latitude, pos.coords.longitude, null);
        if (window.CropWiseGeography) {
          window.CropWiseGeography.confirmGpsLocation(pos.coords.latitude, pos.coords.longitude);
        }
      },
      () => CropWise.toast("Could not access your location. Try search or coordinates instead.", "error"),
      { timeout: 10000 }
    );
  },

  async setLocation(lat, lon, name) {
    CropWise.state.selectedLocation = { lat, lon, name };

    if (this.map) {
      if (this.marker) this.map.removeLayer(this.marker);
      this.marker = L.marker([lat, lon]).addTo(this.map);
      this.map.setView([lat, lon], 11);
    }

    document.getElementById("latInput").value = lat.toFixed(5);
    document.getElementById("lonInput").value = lon.toFixed(5);

    const box = document.getElementById("selectedLocationBox");
    box.classList.remove("hidden");
    document.getElementById("selectedLocationName").textContent = name || "Selected location";
    document.getElementById("selectedLocationCoords").textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    document.getElementById("selectedLocationElevation").textContent = "Fetching elevation…";

    // Reverse geocode for a display name if none provided
    if (!name) {
      try {
        const res = await fetch(`/api/location/reverse?lat=${lat}&lon=${lon}`);
        const data = await res.json();
        if (data.result) {
          CropWise.state.selectedLocation.name = data.result.display_name;
          document.getElementById("selectedLocationName").textContent = data.result.display_name;
        }
      } catch (e) { /* silent - name stays generic */ }
    }

    // Notify prediction module that location changed (fetches env profile for assisted/expert prefill)
    if (window.CropWisePrediction) {
      window.CropWisePrediction.onLocationChanged(lat, lon);
    }
  },
};

window.CropWiseMap = CropWiseMap;

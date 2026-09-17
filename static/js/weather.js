/* ==========================================================================
   CropWise V2 — weather.js
   Fetches and renders the Weather & Climate section (current + 7-day).
   ========================================================================== */

const CropWiseWeather = {
  chart: null,

  async load(lat, lon) {
    document.getElementById("weatherEmpty").classList.add("hidden");
    document.getElementById("weatherContent").classList.remove("hidden");

    const statsEl = document.getElementById("weatherCurrentStats");
    statsEl.innerHTML = `<div class="small-muted">Loading current weather…</div>`;

    try {
      const res = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
      const data = await res.json();

      if (!data.current) {
        statsEl.innerHTML = `<div class="small-muted">Weather data is currently unavailable for this location.</div>`;
        return;
      }

      const c = data.current;
      statsEl.innerHTML = `
        <div class="stat-card">
          <span class="stat-label">Temperature</span>
          <span class="stat-value">${CropWise.formatNumber(c.temperature_c)}°C</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Humidity</span>
          <span class="stat-value">${CropWise.formatNumber(c.humidity_pct, 0)}%</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Precipitation</span>
          <span class="stat-value">${CropWise.formatNumber(c.precipitation_mm)} mm</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Wind Speed</span>
          <span class="stat-value">${CropWise.formatNumber(c.wind_speed_kmh)} km/h</span>
        </div>
      `;

      this.renderForecastChart(data.forecast_7day);

    } catch (e) {
      statsEl.innerHTML = `<div class="small-muted">Could not load weather data.</div>`;
    }
  },

  renderForecastChart(forecast) {
    const canvas = document.getElementById("weatherForecastChart");
    canvas.innerHTML = "";

    if (!forecast || !forecast.dates || forecast.dates.length === 0) {
      canvas.innerHTML = `<p class="small-muted">7-day forecast unavailable.</p>`;
      return;
    }

    const c = document.createElement("canvas");
    canvas.appendChild(c);

    const labels = forecast.dates.map(d => new Date(d).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' }));

    if (this.chart) this.chart.destroy();

    this.chart = new Chart(c.getContext("2d"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            type: "line",
            label: "Max Temp (°C)",
            data: forecast.temp_max,
            borderColor: "#C9A227",
            backgroundColor: "#C9A227",
            yAxisID: "y",
            tension: 0.3,
          },
          {
            type: "line",
            label: "Min Temp (°C)",
            data: forecast.temp_min,
            borderColor: "#3E7089",
            backgroundColor: "#3E7089",
            yAxisID: "y",
            tension: 0.3,
          },
          {
            type: "bar",
            label: "Precipitation (mm)",
            data: forecast.precipitation,
            backgroundColor: "rgba(31, 61, 43, 0.25)",
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          y: { type: "linear", position: "left", title: { display: true, text: "°C" } },
          y1: { type: "linear", position: "right", title: { display: true, text: "mm" }, grid: { drawOnChartArea: false } },
        },
      },
    });
  },
};

window.CropWiseWeather = CropWiseWeather;

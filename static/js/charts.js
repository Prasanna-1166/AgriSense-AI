/* ==========================================================================
   CropWise V2 — charts.js
   Crop comparison table rendering.
   ========================================================================== */

const CropWiseCharts = {
  renderComparison(data) {
    document.getElementById("comparisonEmpty").classList.add("hidden");
    document.getElementById("comparisonContent").classList.remove("hidden");

    const crops = (data.ranked_crops || []).slice(0, 4);
    const table = document.getElementById("comparisonTable");

    if (crops.length === 0) {
      table.innerHTML = `<tr><td>No crops to compare.</td></tr>`;
      return;
    }

    const irrigation = (data.farm && data.farm.irrigation) || "—";

    let html = "<thead><tr><th>Metric</th>";
    crops.forEach(c => {
      html += `<th>${c.icon} ${this.capitalize(c.crop)}</th>`;
    });
    html += "</tr></thead><tbody>";

    const rows = [
      ["Suitability", c => `${c.suitability_pct}%`],
      ["Estimated yield (t/ha)", c => CropWise.formatNumber(c.predicted_yield_t_per_ha)],
      ["Yield range (t/ha)", c => `${CropWise.formatNumber(c.yield_range_t_per_ha.low)} – ${CropWise.formatNumber(c.yield_range_t_per_ha.high)}`],
      ["Total production (t)", c => CropWise.formatNumber(c.predicted_total_production_t)],
      ["Irrigation availability", () => this.capitalize(irrigation)],
    ];

    rows.forEach(([label, fn]) => {
      html += `<tr><td><strong>${label}</strong></td>`;
      crops.forEach(c => { html += `<td>${fn(c)}</td>`; });
      html += `</tr>`;
    });

    html += "</tbody>";
    table.innerHTML = html;
  },

  capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
  },
};

window.CropWiseCharts = CropWiseCharts;

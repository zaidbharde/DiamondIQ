const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const toast = document.querySelector("#toast");
const loader = document.querySelector("#loader");

let currentPrediction = null;
let contributionChart;
let featureChart;
let comparisonChart;

const formatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const numericRules = {
  carat: [0.1, 5, "Carat must be between 0.1 and 5.0"],
  depth: [40, 80, "Depth must be between 40% and 80%"],
  table: [40, 80, "Table must be between 40% and 80%"],
  x: [1, 15, "X must be between 1.0 and 15.0 mm"],
  y: [1, 15, "Y must be between 1.0 and 15.0 mm"],
  z: [0.5, 10, "Z must be between 0.5 and 10.0 mm"],
};

/* ─── Navigation ─── */
function showPage(pageId) {
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  const page = document.querySelector(`#${pageId}`);
  if (page) page.classList.add("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ─── Toast ─── */
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2600);
}

/* ─── Loader ─── */
function setLoading(isLoading) {
  loader.hidden = !isLoading;
}

/* ─── Validation ─── */
function validateField(input) {
  const error = input.parentElement.querySelector(".error");
  if (!error) return true;
  error.textContent = "";

  if (!input.value || input.value.trim() === "") {
    error.textContent = "Required";
    return false;
  }

  if (input.type === "number" || input.tagName === "INPUT") {
    const rule = numericRules[input.name];
    if (rule) {
      const value = Number(input.value);
      const [min, max, msg] = rule;
      if (isNaN(value) || value < min || value > max) {
        error.textContent = msg;
        return false;
      }
    }
  }

  return true;
}

function validateForm() {
  const form = document.querySelector("#predictionForm");
  const fields = form.querySelectorAll("[name]");
  let valid = true;
  fields.forEach((field) => {
    if (!validateField(field)) valid = false;
  });
  return valid;
}

function formPayload() {
  const form = document.querySelector("#predictionForm");
  const data = {};
  form.querySelectorAll("[name]").forEach((field) => {
    data[field.name] = field.value;
  });
  return data;
}

/* ─── API ─── */
async function submitPrediction(event) {
  event.preventDefault();
  if (!validateForm()) {
    showToast("Fix the highlighted fields first.");
    return;
  }

  setLoading(true);
  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(formPayload()),
    });
    const data = await response.json();
    if (!data.ok) {
      Object.entries(data.errors || {}).forEach(([field, message]) => {
        const errEl = document.querySelector(`[data-error="${field}"]`);
        if (errEl) errEl.textContent = message;
      });
      showToast(data.errors?.global || "Prediction failed.");
      return;
    }

    currentPrediction = data.prediction;
    renderResult(currentPrediction);
    renderCharts(currentPrediction);
    updateMetrics(data.metrics);
    await refreshHistory();
    showPage("result");
    showToast("Prediction saved successfully!");
  } catch (error) {
    showToast("Could not reach the prediction API.");
  } finally {
    setLoading(false);
  }
}

/* ─── Render Result ─── */
function renderResult(prediction) {
  const inputs = prediction.inputs;
  const container = document.querySelector("#resultContent");
  const report = prediction.report || {};
  const qual = report.quality_score || 0;
  const rec = report.recommendation || { label: "Standard", badge: "average" };
  const conf = prediction.confidence;

  // Input summary items
  const inputItems = [
    { label: "Carat", value: `${inputs.carat} ct` },
    { label: "Cut", value: inputs.cut },
    { label: "Color", value: inputs.color },
    { label: "Clarity", value: inputs.clarity },
    { label: "Depth", value: `${inputs.depth}%` },
    { label: "Table", value: `${inputs.table}%` },
    { label: "X", value: `${inputs.x} mm` },
    { label: "Y", value: `${inputs.y} mm` },
    { label: "Z", value: `${inputs.z} mm` },
  ];
  if (inputs.shape) inputItems.unshift({ label: "Shape", value: inputs.shape });
  if (inputs.certificate_number) inputItems.push({ label: "Certificate #", value: inputs.certificate_number });

  // Source tracking
  const source = report.source || "manual";
  const sourceBadge = source === "certificate" ? '<span class="source-badge source-cert">Certificate</span>'
    : source === "image" ? '<span class="source-badge source-image">Image Analysis</span>'
    : '<span class="source-badge source-manual">Manual Entry</span>';

  const detected = report.detected || {};
  const hasDetected = Object.keys(detected).length > 0;

  const badgeClass = rec.badge === "premium" ? "badge-premium" : rec.badge === "good" ? "badge-good" : rec.badge === "average" ? "badge-average" : "badge-review";

  const qualBarColor = qual >= 80 ? "#2dd4bf" : qual >= 60 ? "#fbbf24" : qual >= 40 ? "#fb7185" : "#94a3b8";
  const confBarColor = conf >= 85 ? "#2dd4bf" : conf >= 65 ? "#fbbf24" : "#fb7185";

  container.innerHTML = `
    <div class="result-card">
      <p class="result-label">Estimated Market Value</p>
      <div class="result-price">${formatter.format(prediction.price)}</div>
      <div class="result-badge">
        <span>Model <strong>${prediction.model_used}</strong></span>
        <span>${prediction.prediction_time_ms} ms</span>
      </div>
    </div>

    <div class="report-grid">
      <div class="report-card">
        <div class="report-card-header">
          <i data-lucide="gauge" style="width:16px;height:16px;"></i>
          <span>Diamond Quality Score</span>
        </div>
        <div class="report-score-value" style="color:${qualBarColor};">${qual}</div>
        <div class="progress-track">
          <div class="progress-fill" style="width:${qual}%;background:${qualBarColor};"></div>
        </div>
        <p class="report-score-label">out of 100</p>
        <p class="report-card-desc">Based on cut (30%), color (25%), clarity (25%), and carat weight (20%).</p>
      </div>
      <div class="report-card">
        <div class="report-card-header">
          <i data-lucide="shield" style="width:16px;height:16px;"></i>
          <span>Estimated Confidence</span>
        </div>
        <div class="report-score-value" style="color:${confBarColor};">${conf}%</div>
        <div class="progress-track">
          <div class="progress-fill" style="width:${conf}%;background:${confBarColor};"></div>
        </div>
        <p class="report-score-label">Estimated Confidence</p>
        <p class="report-card-desc">Derived from model consistency across feature combinations.</p>
      </div>
      <div class="report-card">
        <div class="report-card-header">
          <i data-lucide="award" style="width:16px;height:16px;"></i>
          <span>Recommendation</span>
        </div>
        <div class="report-rec-badge ${badgeClass}">${rec.label}</div>
        <p class="report-card-desc" style="margin-top:10px;">
          Based on cut (<strong>${inputs.cut}</strong>), color (<strong>${inputs.color}</strong>), clarity (<strong>${inputs.clarity}</strong>), and carat (<strong>${inputs.carat} ct</strong>).
        </p>
      </div>
    </div>

      <div class="report-explanation-card">
        <div class="report-card-header">
          <i data-lucide="sparkles" style="width:16px;height:16px;"></i>
          <span>AI Explanation</span>
        </div>
        <div class="report-explanation-text">${report.ai_explanation || prediction.explanation}</div>
      </div>

      <div class="report-explanation-card" style="margin-top:12px;">
        <div class="report-card-header">
          <i data-lucide="info" style="width:16px;height:16px;"></i>
          <span>Quality Score Details</span>
        </div>
        <div class="report-explanation-text">${report.quality_explanation || "Quality score computed from cut, color, clarity, and carat."}</div>
      </div>

      ${renderXai(prediction)}

      <div class="result-card" style="margin-top:20px;">
        <div class="report-card-header" style="margin-bottom:16px;">
          <i data-lucide="list" style="width:16px;height:16px;"></i>
          <span>Input Summary</span>
        </div>
        <div class="report-meta-bar">
          ${sourceBadge}
          <span class="report-timestamp">${report.timestamp || prediction.created_at || ""}</span>
        </div>
        <div class="result-summary">
          ${inputItems.map((item) => {
            const key = item.label.toLowerCase().replace(/[^a-z]/g, "");
            const detectedVal = hasDetected ? detected[key] || detected[item.label.toLowerCase()] : null;
            const edited = detectedVal && String(detectedVal) !== String(item.value).replace(/[^0-9A-Za-z\s]/g, "").trim();
            const showDiff = detectedVal && String(detectedVal) !== String(item.value);
            return `
              <div class="result-summary-item">
                <span>${item.label}</span>
                <span>${item.value}${showDiff ? ` <span class="edited-badge">edited</span>` : ""}</span>
              </div>
            `;
          }).join("")}
        </div>
        ${hasDetected ? `
        <details class="detected-details">
          <summary>Show original detected values</summary>
          <div class="detected-grid">
            ${Object.entries(detected).map(([k, v]) => `
              <div class="detected-item">
                <span>${k}</span>
                <span>${v}</span>
              </div>
            `).join("")}
          </div>
        </details>
        ` : ""}
      </div>

    <div class="charts-grid">
      <div class="chart-card">
        <h4>Feature Contribution</h4>
        <canvas id="contributionChart" height="200"></canvas>
      </div>
      <div class="chart-card">
        <h4>Input Overview</h4>
        <canvas id="featureChart" height="200"></canvas>
      </div>
      <div class="chart-card full">
        <h4>Price Comparison</h4>
        <canvas id="comparisonChart" height="120"></canvas>
      </div>
    </div>

    <div class="result-actions">
      <button class="btn-icon" id="copyResult" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
        Copy Report
      </button>
      <button class="btn-icon" id="printResult" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
        Print Report
      </button>
      <button class="btn-icon" id="pdfResult" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/></svg>
        PDF Report
      </button>
      <button class="btn-icon" id="shareResult" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" x2="12" y1="2" y2="15"/></svg>
        Share Report
      </button>
      <button class="btn-icon" id="newPrediction" type="button">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
        New Prediction
      </button>
    </div>
  `;

  document.querySelector("#copyResult").addEventListener("click", copyResult);
  document.querySelector("#shareResult").addEventListener("click", shareResult);
  document.querySelector("#pdfResult").addEventListener("click", downloadPdf);
  document.querySelector("#printResult").addEventListener("click", printReport);
  document.querySelector("#newPrediction").addEventListener("click", () => showPage("manualEntry"));
  lucide.createIcons();
}

/* ─── XAI ─── */
function renderXai(prediction) {
  const xai = prediction.xai;
  if (!xai || !xai.most_influential) return "";

  const posFactors = (xai.positive_factors || []).map(f => `
    <div class="xai-factor">
      <span class="xai-factor-icon pos"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg></span>
      <div class="xai-factor-text">
        <strong>${f.feature}</strong>
        <span class="xai-factor-reason">${f.reason}</span>
      </div>
      <span class="xai-impact">+₹${f.impact.toLocaleString("en-IN")}</span>
    </div>
  `).join("");

  const negFactors = (xai.negative_factors || []).map(f => `
    <div class="xai-factor">
      <span class="xai-factor-icon neg"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg></span>
      <div class="xai-factor-text">
        <strong>${f.feature}</strong>
        <span class="xai-factor-reason">${f.reason}</span>
      </div>
      <span class="xai-impact" style="color:var(--text-muted);">₹${f.impact.toLocaleString("en-IN")}</span>
    </div>
  `).join("");

  const maxImpact = Math.max(...xai.most_influential.map(i => i.impact_percent), 1);
  const influentialHtml = xai.most_influential.map(i => `
    <div class="xai-influential-item">
      <span style="width:100px;flex-shrink:0;color:var(--text-secondary);font-size:0.78rem;">${i.feature}</span>
      <div class="xai-influential-bar">
        <div class="xai-influential-fill" style="width:${(i.impact_percent / maxImpact) * 100}%;"></div>
      </div>
      <span style="width:40px;text-align:right;font-weight:700;font-size:0.78rem;color:var(--accent);">${i.impact_percent}%</span>
    </div>
  `).join("");

  return `
    <div class="report-explanation-card" style="margin-top:12px;">
      <div class="report-card-header">
        <i data-lucide="brain" style="width:16px;height:16px;"></i>
        <span>Why This Value? — Explainable AI</span>
      </div>
      <div class="xai-grid">
        <div class="xai-card">
          <div class="xai-card-title">
            <i data-lucide="trending-up" style="width:14px;height:14px;color:#2dd4bf;"></i>
            Positive Factors (${posFactors ? xai.positive_factors.length : 0})
          </div>
          ${posFactors || '<p style="color:var(--text-muted);font-size:0.82rem;">No strong positive factors identified.</p>'}
        </div>
        <div class="xai-card">
          <div class="xai-card-title">
            <i data-lucide="trending-down" style="width:14px;height:14px;color:#fb7185;"></i>
            Negative Factors (${negFactors ? xai.negative_factors.length : 0})
          </div>
          ${negFactors || '<p style="color:var(--text-muted);font-size:0.82rem;">No significant negative factors identified.</p>'}
        </div>
      </div>
      <div class="xai-influential">
        <div class="report-card-header" style="justify-content:flex-start;margin-bottom:10px;">
          <i data-lucide="bar-chart-3" style="width:14px;height:14px;"></i>
          <span>Most Influential Features</span>
        </div>
        ${influentialHtml}
      </div>
    </div>
  `;
}

/* ─── Dashboard Charts ─── */
let priceDistChart, qualityDistChart, timelineChart, recBreakdownChart;

function renderDashboardCharts(metrics) {
  const dists = metrics.distributions;
  if (!dists) return;

  const textColor = getComputedStyle(document.body).getPropertyValue("--text").trim();
  const mutedColor = getComputedStyle(document.body).getPropertyValue("--text-muted").trim();
  const chartBase = (id, emptyId) => {
    const el = document.querySelector(id);
    const empty = document.querySelector(emptyId);
    if (!el) return null;
    empty.style.display = "none";
    return { el, empty };
  };

  const opts = (title) => ({
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: { ticks: { color: mutedColor, font: { size: 9 } }, grid: { display: false } },
      y: { ticks: { color: mutedColor, font: { size: 9 } }, grid: { color: "rgba(255,255,255,0.04)" }, beginAtZero: true },
    },
  });

  // Price Distribution
  if (dists.price_distribution && dists.price_distribution.length) {
    const c = chartBase("#priceDistChart", "#priceDistEmpty");
    if (c) {
      priceDistChart?.destroy();
      priceDistChart = new Chart(c.el, {
        type: "bar",
        data: {
          labels: dists.price_distribution.map(d => d.label),
          datasets: [{ label: "Count", data: dists.price_distribution.map(d => d.count), backgroundColor: "#38bdf8", borderRadius: 4 }],
        },
        options: opts("Price Distribution"),
      });
    }
  } else {
    document.querySelector("#priceDistEmpty").style.display = "block";
  }

  // Quality Distribution
  if (dists.quality_distribution && dists.quality_distribution.length) {
    const c = chartBase("#qualityDistChart", "#qualityDistEmpty");
    if (c) {
      qualityDistChart?.destroy();
      qualityDistChart = new Chart(c.el, {
        type: "bar",
        data: {
          labels: dists.quality_distribution.map(d => d.label),
          datasets: [{ label: "Count", data: dists.quality_distribution.map(d => d.count), backgroundColor: "#2dd4bf", borderRadius: 4 }],
        },
        options: opts("Quality Distribution"),
      });
    }
  } else {
    document.querySelector("#qualityDistEmpty").style.display = "block";
  }

  // Timeline
  if (dists.timeline && dists.timeline.length > 1) {
    const c = chartBase("#timelineChart", "#timelineEmpty");
    if (c) {
      timelineChart?.destroy();
      timelineChart = new Chart(c.el, {
        type: "line",
        data: {
          labels: dists.timeline.map(d => d.date),
          datasets: [{
            label: "Price", data: dists.timeline.map(d => d.price),
            borderColor: "#38bdf8", backgroundColor: "rgba(56,189,248,0.08)",
            fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: "#38bdf8",
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: mutedColor, font: { size: 9 }, maxTicksLimit: 8 }, grid: { display: false } },
            y: { ticks: { color: mutedColor, font: { size: 9 } }, grid: { color: "rgba(255,255,255,0.04)" } },
          },
        },
      });
    }
  } else {
    document.querySelector("#timelineEmpty").style.display = "block";
  }

  // Recommendation Breakdown
  if (dists.recommendation_breakdown && dists.recommendation_breakdown.length) {
    const c = chartBase("#recBreakdownChart", "#recBreakdownEmpty");
    if (c) {
      const recColors = ["#2dd4bf", "#38bdf8", "#fbbf24", "#fb7185", "#a855f7", "#94a3b8"];
      recBreakdownChart?.destroy();
      recBreakdownChart = new Chart(c.el, {
        type: "doughnut",
        data: {
          labels: dists.recommendation_breakdown.map(d => d.label),
          datasets: [{ data: dists.recommendation_breakdown.map(d => d.count), backgroundColor: recColors.slice(0, dists.recommendation_breakdown.length) }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          plugins: {
            legend: { position: "bottom", labels: { color: mutedColor, font: { size: 9 } } },
          },
        },
      });
    }
  } else {
    document.querySelector("#recBreakdownEmpty").style.display = "block";
  }
}

/* ─── Charts ─── */
function chartOptions() {
  const body = document.body;
  const text = getComputedStyle(body).getPropertyValue("--text").trim();
  const muted = getComputedStyle(body).getPropertyValue("--text-muted").trim();
  return {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: { color: text, font: { size: 11 } },
      },
    },
    scales: {
      x: {
        ticks: { color: muted, font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.06)" },
      },
      y: {
        ticks: { color: muted, font: { size: 10 } },
        grid: { color: "rgba(255,255,255,0.06)" },
      },
    },
  };
}

function renderCharts(prediction) {
  const contributions = prediction.contributions;
  const inputs = prediction.inputs;
  const colors = ["#38bdf8", "#2dd4bf", "#a7f3d0", "#fbbf24", "#fb7185", "#c084fc"];

  contributionChart?.destroy();
  const cc = document.querySelector("#contributionChart");
  if (cc) {
    contributionChart = new Chart(cc, {
      type: "doughnut",
      data: {
        labels: contributions.map((c) => c.feature),
        datasets: [{ data: contributions.map((c) => c.score), backgroundColor: colors }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { position: "bottom", labels: { color: getComputedStyle(document.body).getPropertyValue("--text").trim(), font: { size: 10 } } },
        },
      },
    });
  }

  featureChart?.destroy();
  const fc = document.querySelector("#featureChart");
  if (fc) {
    featureChart = new Chart(fc, {
      type: "bar",
      data: {
        labels: ["Carat", "Depth", "Table", "X", "Y", "Z"],
        datasets: [{
          label: "Input values",
          data: [inputs.carat, inputs.depth, inputs.table, inputs.x, inputs.y, inputs.z],
          backgroundColor: "#38bdf8",
          borderRadius: 4,
        }],
      },
      options: chartOptions(),
    });
  }

  comparisonChart?.destroy();
  const cmp = document.querySelector("#comparisonChart");
  if (cmp) {
    comparisonChart = new Chart(cmp, {
      type: "bar",
      data: {
        labels: ["Affordable", "Mid Market", "Premium", "This Prediction"],
        datasets: [{
          label: "Price",
          data: [1200, 4500, 9500, prediction.price],
          backgroundColor: ["#94a3b8", "#2dd4bf", "#fbbf24", "#38bdf8"],
          borderRadius: 4,
        }],
      },
      options: chartOptions(),
    });
  }
}

/* ─── History ─── */
let currentPage = 1;
let totalPages = 1;

function renderHistory(items) {
  const tbody = document.querySelector("#historyBody");
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px;">No predictions yet</td></tr>`;
    return;
  }

  tbody.innerHTML = items
    .map(
      (item) => {
        const badge = item.recommendation_badge === "premium" ? "badge-premium"
          : item.recommendation_badge === "good" ? "badge-good"
          : item.recommendation_badge === "average" ? "badge-average"
          : "badge-review";
        return `
    <tr data-id="${item.id}">
      <td>${formatter.format(item.price)}</td>
      <td>${item.inputs.carat} ct | ${item.inputs.cut} | ${item.inputs.color} | ${item.inputs.clarity}</td>
      <td>${item.quality_score ? `<span class="hist-quality ${badge}">${item.quality_score}</span>` : "—"}</td>
      <td style="font-size:0.78rem;color:var(--text-muted);">${item.created_at ? item.created_at.slice(0, 10) : ""}</td>
      <td>
        <button class="history-delete" data-delete="${item.id}" title="Delete">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </td>
    </tr>
  `}).join("");
}

function renderPagination(page, pages) {
  const container = document.querySelector("#historyPagination");
  if (!container) return;
  currentPage = page;
  totalPages = pages;

  if (pages <= 1) {
    container.style.display = "none";
    return;
  }
  container.style.display = "flex";

  let html = `<button class="page-btn" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>&laquo; Prev</button>`;
  for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) {
    html += `<button class="page-btn ${i === page ? "active" : ""}" data-page="${i}">${i}</button>`;
  }
  html += `<button class="page-btn" data-page="${page + 1}" ${page >= pages ? "disabled" : ""}>Next &raquo;</button>`;
  html += `<span class="page-info">Page ${page} of ${pages}</span>`;
  container.innerHTML = html;

  container.querySelectorAll(".page-btn:not(:disabled)").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = parseInt(btn.dataset.page);
      if (p && p !== currentPage) refreshHistory(p);
    });
  });
}

async function refreshHistory(page) {
  const search = encodeURIComponent(document.querySelector("#historySearch")?.value || "");
  const sort = encodeURIComponent(document.querySelector("#historySort")?.value || "newest");
  const pg = page || currentPage || 1;
  try {
    const response = await fetch(`/history?search=${search}&sort=${sort}&page=${pg}`);
    const data = await response.json();
    renderHistory(data.items || data.history || []);
    renderPagination(data.page || 1, data.pages || 1);
    updateMetrics(data.metrics);
    renderDashboardCharts(data.metrics);
    document.querySelector("#historyEmpty").style.display = (data.total === 0) ? "block" : "none";
  } catch {
    // silent
  }
}

function updateMetrics(metrics) {
  const el = (id) => document.querySelector(id);
  if (el("#metricTotal")) el("#metricTotal").textContent = metrics.total;
  if (el("#metricAverage")) el("#metricAverage").textContent = formatter.format(metrics.average_price);
  if (el("#metricHighest")) el("#metricHighest").textContent = formatter.format(metrics.highest_price);
  if (el("#metricLowest")) el("#metricLowest").textContent = formatter.format(metrics.lowest_price);
  if (el("#metricAvgQuality")) el("#metricAvgQuality").textContent = (metrics.average_quality || 0).toFixed(1) + "%";
}

async function deleteHistory(id) {
  try {
    const response = await fetch(`/history/${id}`, {
      method: "DELETE",
      headers: { "X-CSRFToken": csrfToken },
    });
    const data = await response.json();
    if (data.ok) {
      showToast("Prediction deleted.");
      await refreshHistory();
    }
  } catch {
    showToast("Could not delete prediction.");
  }
}

/* ─── Result Actions ─── */
function copyResult() {
  if (!currentPrediction) return;
  const p = currentPrediction;
  const r = p.report || {};
  const rec = (r.recommendation || {}).label || "Standard";
  const text = [
    "=== AI Diamond Valuation Report ===",
    `Estimated Market Value: ${formatter.format(p.price)}`,
    `Quality Score: ${r.quality_score || "N/A"} / 100`,
    `Recommendation: ${rec}`,
    `Estimated Confidence: ${p.confidence}%`,
    `Model: ${p.model_used}`,
    "",
    "Inputs:",
    ...Object.entries(p.inputs).map(([k, v]) => `  ${k.replace(/_/g, " ")}: ${v}`),
    "",
    `Explanation: ${p.explanation}`,
    "",
    "--- Generated by AI Diamond Valuation Assistant ---",
  ].join("\n");
  navigator.clipboard.writeText(text);
  showToast("Report copied.");
}

async function shareResult() {
  if (!currentPrediction) return;
  const p = currentPrediction;
  const r = p.report || {};
  const text = `💎 AI Diamond Valuation: ${formatter.format(p.price)} | Quality: ${r.quality_score || "N/A"}/100 | ${(r.recommendation || {}).label || ""}`;
  if (navigator.share) {
    await navigator.share({ title: "Diamond Valuation Report", text });
  } else {
    await navigator.clipboard.writeText(text);
    showToast("Share text copied.");
  }
}

function downloadPdf() {
  if (!currentPrediction || !window.jspdf) return;
  const p = currentPrediction;
  const r = p.report || {};
  const doc = new window.jspdf.jsPDF();
  const pageW = doc.internal.pageSize.getWidth();
  let y = 16;

  // Logo / Branding
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(56, 189, 248);
  doc.text("◆ DiamondIQ", 18, y); y += 4;
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text("AI Diamond Valuation Assistant", 18, y); y += 10;

  // Separator line
  doc.setDrawColor(56, 189, 248);
  doc.setLineWidth(0.5);
  doc.line(18, y, pageW - 18, y); y += 8;

  // Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.setTextColor(30, 41, 59);
  doc.text("Valuation Report", 18, y); y += 10;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(100, 116, 139);
  doc.text(`Generated: ${r.timestamp || new Date().toISOString().slice(0, 10)}`, 18, y);
  doc.text(`Source: ${r.source || "manual"}`, pageW - 18, y, { align: "right" }); y += 8;

  // Estimated Market Value
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(30, 41, 59);
  doc.text("Estimated Market Value", 18, y); y += 6;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(56, 189, 248);
  doc.text(formatter.format(p.price), 18, y); y += 10;

  // Score row
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(30, 41, 59);
  doc.text(`Quality Score: ${r.quality_score || "N/A"} / 100`, 18, y);
  doc.text(`Confidence: ${p.confidence}%`, 80, y);
  doc.text(`Recommendation: ${(r.recommendation || {}).label || "Standard"}`, 140, y); y += 8;

  doc.text(`Model: ${p.model_used} (${p.prediction_time_ms} ms)`, 18, y); y += 10;

  // Separator
  doc.setDrawColor(226, 232, 240);
  doc.line(18, y, pageW - 18, y); y += 8;

  // Input Summary
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(30, 41, 59);
  doc.text("Input Summary", 18, y); y += 7;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const inps = p.inputs;
  const inputLines = [
    `Carat: ${inps.carat} ct | Cut: ${inps.cut} | Color: ${inps.color} | Clarity: ${inps.clarity}`,
    `Depth: ${inps.depth}% | Table: ${inps.table}% | X: ${inps.x} mm | Y: ${inps.y} mm | Z: ${inps.z} mm`,
  ];
  if (inps.shape) inputLines.unshift(`Shape: ${inps.shape}`);
  if (inps.certificate_number) inputLines.push(`Certificate: ${inps.certificate_number}`);
  inputLines.forEach((line) => {
    if (y > 265) { doc.addPage(); y = 22; }
    doc.text(line, 18, y); y += 6;
  });
  y += 4;

  // Detected values (if available)
  const detected = r.detected || {};
  if (Object.keys(detected).length > 0) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text("Original Detected Values", 18, y); y += 6;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    Object.entries(detected).forEach(([k, v]) => {
      if (y > 270) { doc.addPage(); y = 22; }
      doc.text(`  ${k}: ${v}`, 18, y); y += 5;
    });
    y += 4;
  }

  // AI Explanation
  if (y > 250) { doc.addPage(); y = 22; }
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(30, 41, 59);
  doc.text("AI Explanation", 18, y); y += 7;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(71, 85, 105);
  const explines = doc.splitTextToSize(r.ai_explanation || p.explanation, 175);
  if (y + explines.length * 5.5 > 270) { doc.addPage(); y = 22; }
  doc.text(explines, 18, y); y += explines.length * 5.5 + 6;

  // Quality Score Details
  if (r.quality_explanation) {
    if (y > 250) { doc.addPage(); y = 22; }
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(30, 41, 59);
    doc.text("Quality Score Details", 18, y); y += 7;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    const qlines = doc.splitTextToSize(r.quality_explanation, 175);
    if (y + qlines.length * 5 > 270) { doc.addPage(); y = 22; }
    doc.text(qlines, 18, y);
  }

  // Footer
  const footerY = doc.internal.pageSize.getHeight() - 10;
  doc.setFont("helvetica", "italic");
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text("Generated by AI Diamond Valuation Assistant", pageW / 2, footerY, { align: "center" });

  doc.save("diamond-valuation-report.pdf");
}

function printReport() {
  if (!currentPrediction) return;
  const p = currentPrediction;
  const r = p.report || {};
  const rec = (r.recommendation || {}).label || "Standard";
  const w = window.open("", "_blank");
  w.document.write(`
    <html><head><title>Diamond Valuation Report</title>
    <style>
      body { font-family: system-ui, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; color: #222; }
      h1 { font-size: 24px; margin-bottom: 4px; }
      h2 { font-size: 18px; margin-top: 28px; margin-bottom: 8px; }
      .price { font-size: 36px; font-weight: 800; color: #0ea5e9; margin: 8px 0; }
      .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 20px 0; }
      .card { padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; }
      .card h3 { font-size: 14px; color: #64748b; margin: 0 0 8px; }
      .card .val { font-size: 24px; font-weight: 700; }
      .rec-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 14px; }
      table { width: 100%; border-collapse: collapse; margin: 12px 0; }
      td, th { text-align: left; padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
      .explanation { padding: 16px; border-left: 3px solid #0ea5e9; background: #f8fafc; border-radius: 4px; line-height: 1.7; }
      .meta { color: #64748b; font-size: 14px; }
      .footer { margin-top: 40px; font-size: 12px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px; }
    </style></head><body>
    <h1>AI Diamond Valuation Report</h1>
    <p class="meta">Generated ${new Date().toLocaleString()}</p>
    <div class="price">${formatter.format(p.price)}</div>
    <p class="meta">Model: ${p.model_used} | Confidence: ${p.confidence}% | ${p.prediction_time_ms} ms</p>
    <div class="grid">
      <div class="card"><h3>Quality Score</h3><div class="val">${r.quality_score || "N/A"}</div></div>
      <div class="card"><h3>Recommendation</h3><div class="rec-badge">${rec}</div></div>
      <div class="card"><h3>Confidence</h3><div class="val">${p.confidence}%</div></div>
    </div>
    <h2>Input Summary</h2>
    <table>${Object.entries(p.inputs).filter(([k]) => k !== "shape" || p.inputs.shape).map(([k, v]) => `<tr><td style="text-transform:capitalize;">${k.replace(/_/g, " ")}</td><td><strong>${v}</strong></td></tr>`).join("")}</table>
    <h2>AI Explanation</h2>
    <div class="explanation">${p.explanation}</div>
    ${r.quality_explanation ? `<h2>Quality Score Details</h2><div class="explanation">${r.quality_explanation}</div>` : ""}
    <div class="footer">This report is AI-generated and for informational purposes only. Not a certified appraisal.</div>
    <script>window.print();<\/script>
    </body></html>
  `);
  w.document.close();
}

/* ─── Certificate Upload ─── */
let extractedFields = null;

const CUT_OPTIONS = ["Fair", "Good", "Very Good", "Premium", "Ideal"];
const COLOR_OPTIONS = ["D", "E", "F", "G", "H", "I", "J"];
const CLARITY_OPTIONS = ["I1", "SI2", "SI1", "VS2", "VS1", "VVS2", "VVS1", "IF"];

function initUpload() {
  const zone = document.querySelector("#uploadZone");
  const input = document.querySelector("#fileInput");
  const browseBtn = document.querySelector("#browseBtn");

  browseBtn?.addEventListener("click", () => input?.click());
  input?.addEventListener("change", () => {
    if (input.files.length) handleFile(input.files[0]);
  });

  zone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone?.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone?.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  zone?.addEventListener("click", (e) => {
    if (e.target === zone || e.target.closest(".upload-zone-content")) {
      input?.click();
    }
  });

  document.querySelector("#retryUpload")?.addEventListener("click", resetUpload);
  document.querySelector("#continueToPrediction")?.addEventListener("click", continueToPrediction);
}

function handleFile(file) {
  const validTypes = [".pdf", ".jpg", ".jpeg", ".png"];
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!validTypes.includes(ext)) {
    showToast("Unsupported file type. Upload PDF, JPG, JPEG, or PNG.");
    return;
  }
  if (file.size > 16 * 1024 * 1024) {
    showToast("File too large. Maximum size is 16 MB.");
    return;
  }

  showFileInfo(file);
  uploadFile(file);
}

function showFileInfo(file) {
  const zone = document.querySelector("#uploadZoneContent");
  const preview = document.querySelector("#uploadPreview");
  const info = document.querySelector("#uploadFileInfo");
  const progressWrap = document.querySelector("#uploadProgressWrap");
  const progressBar = document.querySelector("#uploadProgressBar");

  zone.style.display = "none";
  preview.style.display = "block";
  progressWrap.style.display = "block";
  progressBar.style.width = "0%";

  const size = (file.size / 1024 / 1024).toFixed(1);
  info.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
    <span><strong>${file.name}</strong> &middot; ${size} MB</span>
  `;
}

function uploadFile(file) {
  const progressBar = document.querySelector("#uploadProgressBar");
  const ocrStatus = document.querySelector("#ocrStatus");
  const extractedCard = document.querySelector("#extractedFieldsCard");

  ocrStatus.style.display = "none";
  extractedCard.style.display = "none";

  // Simulate upload progress
  let progress = 0;
  const interval = setInterval(() => {
    progress += Math.random() * 15 + 5;
    if (progress >= 95) {
      progress = 95;
      clearInterval(interval);
    }
    progressBar.style.width = Math.min(progress, 95) + "%";
  }, 200);

  const formData = new FormData();
  formData.append("file", file);

  fetch("/upload-certificate", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      clearInterval(interval);
      progressBar.style.width = "100%";
      setTimeout(() => showOcrResult(data), 400);
    })
    .catch(() => {
      clearInterval(interval);
      showToast("Upload failed. Try again.");
      resetUpload();
    });
}

function showOcrResult(data) {
  const ocrStatus = document.querySelector("#ocrStatus");
  const extractedCard = document.querySelector("#extractedFieldsCard");
  const certBadge = document.querySelector("#certTypeBadge");
  const fieldsContainer = document.querySelector("#ocrFields");

  // Show OCR status with steps
  ocrStatus.style.display = "block";
  animateOcrSteps();

  setTimeout(() => {
    ocrStatus.style.display = "none";

    if (!data.ok) {
      showToast(data.error || "OCR processing failed.");
      resetUpload();
      return;
    }

    extractedCard.style.display = "block";
    certBadge.textContent = data.certificate_type || "Unknown";
    extractedFields = data.fields;

    renderExtractedFields(fieldsContainer, data.fields);
    lucide.createIcons();
    showToast("Certificate processed successfully!");
  }, 1800);
}

function animateOcrSteps() {
  const step1 = document.querySelector("#ocrStep1");
  const step2 = document.querySelector("#ocrStep2");
  const step3 = document.querySelector("#ocrStep3");
  const step4 = document.querySelector("#ocrStep4");

  step1.classList.add("active");
  setTimeout(() => {
    step1.classList.remove("active");
    step1.classList.add("done");
    step2.classList.add("active");
  }, 700);
  setTimeout(() => {
    step2.classList.remove("active");
    step2.classList.add("done");
    step3.classList.add("active");
  }, 1400);
  setTimeout(() => {
    step3.classList.remove("active");
    step3.classList.add("done");
    step4.style.display = "flex";
    step4.classList.add("active");
    setTimeout(() => {
      step4.classList.remove("active");
      step4.classList.add("done");
    }, 300);
  }, 2100);
}

function renderExtractedFields(container, fields) {
  // Check for low confidence fields
  const lowConfFields = Object.entries(fields).filter(
    ([_, v]) => v && v.confidence < 45
  );

  let warningHtml = "";
  if (lowConfFields.length > 0) {
    warningHtml = `
      <div style="display:flex;align-items:center;gap:8px;padding:10px 14px;border-radius:var(--radius-sm);background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.2);margin-bottom:16px;font-size:0.85rem;color:var(--warning);">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
        <span>⚠ <strong>Review Recommended</strong> — Some fields have low OCR confidence. Please verify them.</span>
      </div>`;
  }

  const fieldDefs = [
    { key: "shape", label: "Shape", type: "text", placeholder: "e.g. Round Brilliant" },
    { key: "carat", label: "Carat", type: "number", step: "0.01", placeholder: "e.g. 0.70" },
    { key: "cut", label: "Cut", type: "select", options: CUT_OPTIONS },
    { key: "color", label: "Color", type: "select", options: COLOR_OPTIONS },
    { key: "clarity", label: "Clarity", type: "select", options: CLARITY_OPTIONS },
    { key: "depth", label: "Depth (%)", type: "number", step: "0.1", placeholder: "e.g. 61.5" },
    { key: "table", label: "Table (%)", type: "number", step: "0.1", placeholder: "e.g. 57.0" },
    { key: "x", label: "X (mm)", type: "number", step: "0.01", placeholder: "e.g. 5.70" },
    { key: "y", label: "Y (mm)", type: "number", step: "0.01", placeholder: "e.g. 5.72" },
    { key: "z", label: "Z (mm)", type: "number", step: "0.01", placeholder: "e.g. 3.52" },
    { key: "certificate_number", label: "Certificate #", type: "text", placeholder: "Optional" },
    { key: "polish", label: "Polish", type: "text", placeholder: "Optional" },
    { key: "symmetry", label: "Symmetry", type: "text", placeholder: "Optional" },
    { key: "fluorescence", label: "Fluorescence", type: "text", placeholder: "Optional" },
  ];

  container.innerHTML = warningHtml + fieldDefs
    .map((def) => {
      const field = fields[def.key];
      const hasValue = field && field.value;
      const conf = field ? field.confidence : 0;

      let confClass = "low";
      let confLabel = "⚠ Review Recommended";
      if (conf >= 65) { confClass = "high"; confLabel = "High Confidence"; }
      else if (conf >= 45) { confClass = "medium"; confLabel = "Medium Confidence"; }

      let inputHtml;
      if (def.type === "select") {
        inputHtml = `<select data-ocr-key="${def.key}">
          <option value="">-- Select --</option>
          ${def.options
            .map(
              (opt) =>
                `<option value="${opt}" ${hasValue && opt === field.value ? "selected" : ""}>${opt}</option>`
            )
            .join("")}
        </select>`;
      } else {
        inputHtml = `<input type="${def.type}" data-ocr-key="${def.key}" 
          ${def.step ? `step="${def.step}"` : ""}
          placeholder="${def.placeholder}" 
          value="${hasValue ? field.value : ""}" />`;
      }

      const confHtml = hasValue
        ? `<span class="conf-badge ${confClass}">${confLabel}</span>`
        : `<span class="ocr-field-empty">Not detected</span>`;

      return `
        <div class="ocr-field">
          <span class="ocr-field-label">${def.label}</span>
          ${inputHtml}
          ${confHtml}
        </div>
      `;
    })
    .join("");
}

function resetUpload() {
  const zone = document.querySelector("#uploadZoneContent");
  const preview = document.querySelector("#uploadPreview");
  const progressWrap = document.querySelector("#uploadProgressWrap");
  const ocrStatus = document.querySelector("#ocrStatus");
  const extractedCard = document.querySelector("#extractedFieldsCard");
  const fileInput = document.querySelector("#fileInput");

  zone.style.display = "block";
  preview.style.display = "none";
  progressWrap.style.display = "none";
  ocrStatus.style.display = "none";
  extractedCard.style.display = "none";
  if (fileInput) fileInput.value = "";
  extractedFields = null;
}

function continueToPrediction() {
  const fieldsContainer = document.querySelector("#ocrFields");
  const inputs = fieldsContainer.querySelectorAll("[data-ocr-key]");

  // Save original detected values before user edits them
  const detected = {};
  inputs.forEach((el) => {
    const key = el.dataset.ocrKey;
    const field = document.querySelector(`[name="${key}"]`);
    if (field && el.value) {
      field.value = el.value;
      validateField(field);
    }
    // Store detected value from the data attribute or select option
    if (el.value) {
      detected[key] = el.value;
    }
  });

  // Set defaults for required fields if missing
  const required = { depth: 61.5, table: 57, x: 5.5, y: 5.5, z: 3.5 };
  Object.entries(required).forEach(([key, defaultVal]) => {
    const field = document.querySelector(`[name="${key}"]`);
    if (field && !field.value) {
      field.value = defaultVal;
      validateField(field);
    }
  });

  document.querySelector("#inputSource").value = "certificate";
  document.querySelector("#inputDetected").value = JSON.stringify(detected);

  showPage("manualEntry");
  showToast("Certificate data loaded! Review and predict.");
}

/* ─── Image Upload ─── */
let currentImageFile = null;
const IMAGE_SHAPES = ["Round", "Princess", "Cushion", "Emerald", "Oval", "Pear", "Marquise", "Asscher", "Radiant", "Heart"];
const IMAGE_POLISH_GRADES = ["Excellent", "Very Good", "Good", "Fair", "Poor"];

function initImageUpload() {
  const zone = document.querySelector("#imageUploadZone");
  const input = document.querySelector("#imageFileInput");
  const browseBtn = document.querySelector("#imageBrowseBtn");

  browseBtn?.addEventListener("click", () => input?.click());
  input?.addEventListener("change", () => {
    if (input.files.length) handleImageFile(input.files[0]);
  });

  zone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("dragover");
  });
  zone?.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone?.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleImageFile(e.dataTransfer.files[0]);
  });
  zone?.addEventListener("click", (e) => {
    if (e.target === zone || e.target.closest(".upload-zone-content")) {
      input?.click();
    }
  });

  document.querySelector("#retryImageUpload")?.addEventListener("click", resetImageUpload);
  document.querySelector("#continueFromImage")?.addEventListener("click", continueFromImage);
  document.querySelector("#analyzeBtn")?.addEventListener("click", () => {
    if (currentImageFile) uploadImage(currentImageFile);
  });
}

function handleImageFile(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (![".png", ".jpg", ".jpeg", ".webp"].includes(ext)) {
    showToast("Unsupported file type. Upload PNG, JPG, JPEG, or WEBP.");
    return;
  }
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    showToast("File too large. Maximum size is 10 MB.");
    return;
  }

  currentImageFile = file;
  showImagePreview(file);

  const analyzeSection = document.querySelector("#analyzeSection");
  analyzeSection.style.display = "block";
  document.querySelector("#imageSuggestionsCard").style.display = "none";
  document.querySelector("#noApiMsg").style.display = "none";

  lucide.createIcons();
}

function showImagePreview(file) {
  const zone = document.querySelector("#imageUploadZoneContent");
  const preview = document.querySelector("#imageUploadPreview");
  const info = document.querySelector("#imageFileInfo");
  const progressWrap = document.querySelector("#imageUploadProgressWrap");

  zone.style.display = "none";
  preview.style.display = "block";
  progressWrap.style.display = "none";

  const reader = new FileReader();
  reader.onload = (e) => {
    document.querySelector("#imagePreview").src = e.target.result;
  };
  reader.readAsDataURL(file);

  const size = (file.size / 1024 / 1024).toFixed(1);
  info.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
    <span><strong>${file.name}</strong> &middot; ${size} MB</span>
  `;
}

function uploadImage(file) {
  const progressBar = document.querySelector("#imageUploadProgressBar");
  const progressWrap = document.querySelector("#imageUploadProgressWrap");
  const analysisStatus = document.querySelector("#imageAnalysisStatus");
  const suggestionsCard = document.querySelector("#imageSuggestionsCard");

  progressWrap.style.display = "block";
  progressBar.style.width = "0%";
  analysisStatus.style.display = "none";
  suggestionsCard.style.display = "none";
  document.querySelector("#noApiMsg").style.display = "none";

  let progress = 0;
  const interval = setInterval(() => {
    progress += Math.random() * 15 + 5;
    if (progress >= 95) {
      progress = 95;
      clearInterval(interval);
    }
    progressBar.style.width = Math.min(progress, 95) + "%";
  }, 200);

  const formData = new FormData();
  formData.append("file", file);

  fetch("/analyze-image", {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      clearInterval(interval);
      progressBar.style.width = "100%";
      setTimeout(() => showImageAnalysisResult(data), 400);
    })
    .catch(() => {
      clearInterval(interval);
      showToast("Upload failed. Try again.");
      resetImageUpload();
    });
}

function showImageAnalysisResult(data) {
  const analysisStatus = document.querySelector("#imageAnalysisStatus");
  const suggestionsCard = document.querySelector("#imageSuggestionsCard");
  const noApiMsg = document.querySelector("#noApiMsg");

  analysisStatus.style.display = "block";
  animateImageSteps();

  setTimeout(() => {
    analysisStatus.style.display = "none";

    if (!data.ok) {
      showToast(data.error || "Analysis failed.");
      resetImageUpload();
      return;
    }

    if (data.no_api_key) {
      document.querySelector("#noApiText").textContent = data.message;
      noApiMsg.style.display = "flex";
      lucide.createIcons();
      return;
    }

    if (data.fallback) {
      document.querySelector("#noApiText").textContent = data.message || "AI analysis encountered an issue. The provider may be unavailable.";
      noApiMsg.style.display = "flex";
      lucide.createIcons();
      return;
    }

    const badge = document.querySelector("#aiProviderBadge");
    badge.textContent = data.provider ? data.provider.toUpperCase() : "AI";

    suggestionsCard.style.display = "block";
    renderImageSuggestions(data.suggestions);
    lucide.createIcons();
    showToast("Analysis complete!");
  }, 2200);
}

function animateImageSteps() {
  const step1 = document.querySelector("#imgStep1");
  const step2 = document.querySelector("#imgStep2");
  const step3 = document.querySelector("#imgStep3");
  const step4 = document.querySelector("#imgStep4");

  step1.classList.add("active");
  setTimeout(() => {
    step1.classList.remove("active");
    step1.classList.add("done");
    step2.classList.add("active");
  }, 700);
  setTimeout(() => {
    step2.classList.remove("active");
    step2.classList.add("done");
    step3.classList.add("active");
  }, 1400);
  setTimeout(() => {
    step3.classList.remove("active");
    step3.classList.add("done");
    step4.style.display = "flex";
    step4.classList.add("active");
    setTimeout(() => {
      step4.classList.remove("active");
      step4.classList.add("done");
    }, 300);
  }, 2100);
}

function renderImageSuggestions(suggestions) {
  const container = document.querySelector("#imageSuggestionsFields");

  if (!suggestions || Object.keys(suggestions).length === 0) {
    container.innerHTML = `<p style="color:var(--text-secondary);font-size:0.9rem;text-align:center;padding:20px 0;">No characteristics could be determined from this image. Try a clearer photo.</p>`;
    return;
  }

  const shapeVal = suggestions.shape ? suggestions.shape.value : "";
  const shapeConf = suggestions.shape ? suggestions.shape.confidence : 0;
  const cutVal = suggestions.cut ? suggestions.cut.value : "";
  const cutConf = suggestions.cut ? suggestions.cut.confidence : 0;
  const colorVal = suggestions.color ? suggestions.color.value : "";
  const colorConf = suggestions.color ? suggestions.color.confidence : 0;
  const polishVal = suggestions.polish ? suggestions.polish.value : "";
  const polishConf = suggestions.polish ? suggestions.polish.confidence : 0;
  const symmetryVal = suggestions.symmetry ? suggestions.symmetry.value : "";
  const symmetryConf = suggestions.symmetry ? suggestions.symmetry.confidence : 0;

  function confHtml(conf) {
    if (!conf) return `<span class="ocr-field-empty">Not detected</span>`;
    if (conf >= 65) return `<span class="conf-badge high">High Confidence</span>`;
    if (conf >= 45) return `<span class="conf-badge medium">Medium Confidence</span>`;
    return `<span class="conf-badge low">⚠ Review Recommended</span>`;
  }

  container.innerHTML = `
    <div class="ocr-field">
      <span class="ocr-field-label">Shape</span>
      <select data-img-suggestion="shape">
        <option value="">-- Select --</option>
        ${IMAGE_SHAPES.map(s => `<option value="${s}" ${shapeVal === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${confHtml(shapeConf)}
    </div>
    <div class="ocr-field">
      <span class="ocr-field-label">Estimated Cut</span>
      <select data-img-suggestion="cut">
        <option value="">-- Select --</option>
        ${CUT_OPTIONS.map(s => `<option value="${s}" ${cutVal === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${confHtml(cutConf)}
    </div>
    <div class="ocr-field">
      <span class="ocr-field-label">Estimated Color</span>
      <select data-img-suggestion="color">
        <option value="">-- Select --</option>
        ${COLOR_OPTIONS.map(s => `<option value="${s}" ${colorVal === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${confHtml(colorConf)}
    </div>
    <div class="ocr-field">
      <span class="ocr-field-label">Estimated Polish</span>
      <select data-img-suggestion="polish">
        <option value="">-- Select --</option>
        ${IMAGE_POLISH_GRADES.map(s => `<option value="${s}" ${polishVal === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${confHtml(polishConf)}
    </div>
    <div class="ocr-field">
      <span class="ocr-field-label">Estimated Symmetry</span>
      <select data-img-suggestion="symmetry">
        <option value="">-- Select --</option>
        ${IMAGE_POLISH_GRADES.map(s => `<option value="${s}" ${symmetryVal === s ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      ${confHtml(symmetryConf)}
    </div>
  `;
}

function resetImageUpload() {
  const zone = document.querySelector("#imageUploadZoneContent");
  const preview = document.querySelector("#imageUploadPreview");
  const progressWrap = document.querySelector("#imageUploadProgressWrap");
  const analysisStatus = document.querySelector("#imageAnalysisStatus");
  const suggestionsCard = document.querySelector("#imageSuggestionsCard");
  const analyzeSection = document.querySelector("#analyzeSection");
  const noApiMsg = document.querySelector("#noApiMsg");
  const fileInput = document.querySelector("#imageFileInput");

  zone.style.display = "block";
  preview.style.display = "none";
  progressWrap.style.display = "none";
  analysisStatus.style.display = "none";
  suggestionsCard.style.display = "none";
  analyzeSection.style.display = "none";
  noApiMsg.style.display = "none";
  if (fileInput) fileInput.value = "";
  currentImageFile = null;
}

function continueFromImage() {
  const container = document.querySelector("#imageSuggestionsFields");
  const inputs = container.querySelectorAll("[data-img-suggestion]");

  const detected = {};
  inputs.forEach((el) => {
    const key = el.dataset.imgSuggestion;
    const field = document.querySelector(`[name="${key}"]`);
    if (field && el.value) {
      field.value = el.value;
      validateField(field);
      detected[key] = el.value;
    }
  });

  document.querySelector("#inputSource").value = "image";
  document.querySelector("#inputDetected").value = JSON.stringify(detected);

  showPage("manualEntry");
  resetImageUpload();
  showToast("AI suggestions loaded! Review and predict.");
}

/* ─── Theme ─── */
function toggleTheme() {
  document.body.classList.toggle("light");
  localStorage.setItem(
    "diamond-theme",
    document.body.classList.contains("light") ? "light" : "dark"
  );
}

function hydrateTheme() {
  const saved = localStorage.getItem("diamond-theme");
  if (saved === "light") {
    document.body.classList.add("light");
  }
}

/* ─── Collapse Toggle ─── */
function toggleAdvanced() {
  const content = document.querySelector("#advancedContent");
  const toggle = document.querySelector("#advancedToggle");
  const isOpen = content.classList.toggle("open");
  toggle.classList.toggle("open");
  toggle.querySelector("span:last-child").textContent = isOpen ? "Hide" : "Show";
}

/* ─── Event Listeners ─── */
hydrateTheme();
lucide.createIcons();
initUpload();
initImageUpload();

document.addEventListener("click", (event) => {
  const deleteBtn = event.target.closest("[data-delete]");
  if (deleteBtn) {
    const id = deleteBtn.dataset.delete;
    if (id) deleteHistory(id);
  }
});

document.querySelector("#predictionForm")?.addEventListener("submit", submitPrediction);
document.querySelector("#predictionForm")?.addEventListener("input", (event) => {
  if (event.target.name) validateField(event.target);
});

document.querySelector("#themeToggle")?.addEventListener("click", toggleTheme);
document.querySelector("#advancedToggle")?.addEventListener("click", toggleAdvanced);

document.querySelector("#historySearch")?.addEventListener("input", refreshHistory);
document.querySelector("#historySort")?.addEventListener("change", refreshHistory);

document.querySelectorAll("[data-page]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = btn.dataset.page;
    if (page) {
      showPage(page);
      if (page === "dashboard") refreshHistory(1);
    }
  });
});

document.addEventListener("keydown", (event) => {
  if (!event.ctrlKey) return;
  if (event.key === "Enter") {
    event.preventDefault();
    document.querySelector("#predictionForm")?.requestSubmit();
  }
  if (event.key.toLowerCase() === "r") {
    event.preventDefault();
    const form = document.querySelector("#predictionForm");
    if (form) {
      form.reset();
      form.querySelectorAll(".error").forEach((e) => (e.textContent = ""));
      showToast("Form reset.");
    }
  }
  if (event.key.toLowerCase() === "k") {
    event.preventDefault();
    document.querySelector("#historySearch")?.focus();
  }
});

// Render dashboard charts on initial load
setTimeout(() => {
  const metricsEl = document.querySelector("#metricTotal");
  if (metricsEl && metricsEl.textContent !== "0") {
    refreshHistory(1);
  }
}, 300);

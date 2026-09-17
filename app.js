const state = {
  desk: null,
  selectedId: null,
  decisions: [],
};

const $ = (sel) => document.querySelector(sel);

function pct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function fmtTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

async function loadDesk() {
  const response = await fetch("data/desk_snapshot.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to load desk snapshot");
  state.desk = await response.json();
  renderAll();
}

function renderAll() {
  const { desk } = state;
  const v = desk.verdict;
  const edge = v.strategy_edge_validated;

  $("#gate-events").textContent = `${desk.gates.events} events`;
  const chip = $("#chip-edge");
  chip.textContent = edge ? "edge: validated" : "edge: refused";
  chip.className = `status-chip ${edge ? "ok" : "bad"}`;

  $("#gate-row").innerHTML = [
    `clocks ${desk.gates.issuer_clocks_validated}/30`,
    `immutable consensus ${desk.gates.immutable_consensus}/30`,
    `calibration ${v.calibration_successful ? "fit ok" : "refused"}`,
    `paper ${desk.gates.paper}`,
    `live ${desk.gates.live}`,
  ].map((text) => `<span class="gate-chip">${text}</span>`).join("");

  $("#verdict-title").textContent = edge ? "Edge found" : "No trade";
  $("#verdict-body").textContent = edge
    ? "Holdout bake-off cleared cost-aware baselines."
    : "Absorption and calibrated surprise take zero holdout trades after costs. Desk stays advisory.";

  $("#refusal-list").innerHTML = (v.refusal_reasons || [])
    .slice(0, 5)
    .map((r) => `<li>${r}</li>`)
    .join("");

  renderInsights();
  renderRanks();
  renderTable();
  renderRecommendation();

  const first = desk.events[0];
  if (first) selectEvent(first.event_id);
}

function renderInsights() {
  const { desk } = state;
  const events = desk.events;
  const pos = events.filter((e) => e.direction === "positive").length;
  const clocks = desk.gates.issuer_clocks_validated;
  const hold = desk.verdict.holdout_metrics || {};
  const cards = [
    {
      title: "Signal mix",
      body: `${pos} positive / ${events.length - pos} non-positive primary surprises across the joined sample.`,
    },
    {
      title: "Evidence quality",
      body: `Issuer clocks validated ${clocks}/30. Immutable consensus ${desk.gates.immutable_consensus}/30. Evidence stays exploratory.`,
    },
    {
      title: "Holdout skill",
      body: `Direction accuracy ${hold.direction_accuracy == null ? "—" : (hold.direction_accuracy * 100).toFixed(0) + "%"}. MAE ${hold.mae == null ? "—" : hold.mae.toFixed(3)}.`,
    },
  ];
  $("#insight-grid").innerHTML = cards.map((c) => `
    <article class="insight-card">
      <h3>${c.title}</h3>
      <p>${c.body}</p>
    </article>
  `).join("");
}

function renderRanks() {
  const ranks = state.desk.verdict.ranking_by_mean_net || [];
  $("#rank-grid").innerHTML = ranks.slice(0, 6).map((row) => `
    <article class="rank-card">
      <h3>${row.strategy}</h3>
      <p>Mean net ${pct(row.mean_net_return_all_events)} · trades ${row.trade_count}</p>
    </article>
  `).join("");
}

function filteredEvents() {
  const ticker = ($("#filter-ticker").value || "").trim().toUpperCase();
  const direction = $("#filter-direction").value;
  return state.desk.events.filter((event) => {
    if (ticker && !(event.ticker || "").includes(ticker) && !(event.token || "").includes(ticker)) {
      return false;
    }
    if (direction && event.direction !== direction) return false;
    return true;
  });
}

function renderTable() {
  const rows = filteredEvents();
  $("#event-tbody").innerHTML = rows.map((event) => `
    <tr data-id="${event.event_id}" class="${event.event_id === state.selectedId ? "active" : ""}">
      <td><strong>${event.ticker || "—"}</strong><div class="muted">${event.token || ""}</div></td>
      <td>${pct(event.surprise)}</td>
      <td>${event.direction || "—"}</td>
      <td>${pct(event.horizon_return)}</td>
      <td>${event.issuer_clock_validated ? "validated" : "EDGAR"}</td>
    </tr>
  `).join("");
}

function selectEvent(eventId) {
  state.selectedId = eventId;
  const event = state.desk.events.find((item) => item.event_id === eventId);
  if (!event) return;
  renderTable();
  $("#detail-title").textContent = `${event.ticker} · ${event.token}`;
  $("#detail-meta").textContent = `${fmtTime(event.published_at)} · ${event.timestamp_semantics || "clock"} · importance ${event.importance || "—"}`;
  $("#detail-blockers").innerHTML = (event.trade_blockers || ["NONE"])
    .map((b) => `<span class="chip warn">${b}</span>`).join("");
  drawPath(event.path || []);
}

function drawPath(path) {
  const canvas = $("#path-chart");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#f7f7f8";
  ctx.fillRect(0, 0, w, h);
  if (path.length < 2) {
    ctx.fillStyle = "#5c5c63";
    ctx.font = "16px Outfit, sans-serif";
    ctx.fillText("No path observations", 24, h / 2);
    return;
  }
  const xs = path.map((p) => p.t);
  const ys = path.map((p) => p.ret);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 0);
  const pad = 24;
  const scaleX = (t) => pad + ((t - minX) / (maxX - minX || 1)) * (w - pad * 2);
  const scaleY = (v) => h - pad - ((v - minY) / (maxY - minY || 1)) * (h - pad * 2);

  ctx.strokeStyle = "rgba(17,17,17,0.12)";
  ctx.beginPath();
  ctx.moveTo(pad, scaleY(0));
  ctx.lineTo(w - pad, scaleY(0));
  ctx.stroke();

  ctx.strokeStyle = "#ff6a1a";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  path.forEach((point, index) => {
    const x = scaleX(point.t);
    const y = scaleY(point.ret);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderRecommendation() {
  const edge = state.desk.verdict.strategy_edge_validated;
  $("#ai-rec").textContent = edge
    ? "AI recommendation: REVIEW CANDIDATES"
    : "AI recommendation: NO TRADE";
  $("#ai-rec-why").textContent = edge
    ? "Edge gate cleared. Still requires human size/risk approval."
    : "Bake-off refused edge. Paper and live remain blocked. Prefer HOLD.";
}

function answerQuestion(raw) {
  const q = raw.trim().toLowerCase();
  const desk = state.desk;
  if (!q) return "Ask about edge, paper, a ticker, or the bake-off.";

  if (q.includes("paper")) {
    return `Paper is blocked: ${(desk.verdict.paper_refusal_reasons || ["unspecified"]).join(", ")}.`;
  }
  if (q.includes("edge") || q.includes("trade") || q.includes("why")) {
    return `Edge refused. Reasons: ${(desk.verdict.refusal_reasons || []).slice(0, 3).join("; ")}.`;
  }
  if (q.includes("bake") || q.includes("rank") || q.includes("momentum")) {
    const top = (desk.verdict.ranking_by_mean_net || [])[0];
    return top
      ? `Top holdout strategy is ${top.strategy} at ${pct(top.mean_net_return_all_events)} mean net.`
      : "No ranking available.";
  }
  const hit = desk.events.find((event) =>
    q.includes((event.ticker || "").toLowerCase()) ||
    q.includes((event.token || "").toLowerCase()));
  if (hit) {
    selectEvent(hit.event_id);
    return `${hit.ticker}: surprise ${pct(hit.surprise)}, 180m ${pct(hit.horizon_return)}, clock ${hit.issuer_clock_validated ? "validated" : "EDGAR fallback"}.`;
  }
  if (q.includes("clock")) {
    return `Issuer clocks validated ${desk.gates.issuer_clocks_validated}/30.`;
  }
  return "Try: “Why is paper blocked?”, “Show AMD”, or “Who wins the bake-off?”.";
}

function showToast(message) {
  const toast = $("#toast");
  toast.hidden = false;
  toast.textContent = message;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { toast.hidden = true; }, 3200);
}

function exportBrief() {
  const desk = state.desk;
  const selected = desk.events.find((e) => e.event_id === state.selectedId);
  const lines = [
    "IAA Desk research brief",
    `Track: ${desk.track}`,
    `Edge validated: ${desk.verdict.strategy_edge_validated}`,
    `Paper validated: ${desk.verdict.paper_execution_validated}`,
    `Refusals: ${(desk.verdict.refusal_reasons || []).join(", ")}`,
    selected ? `Focus: ${selected.ticker} ${selected.event_id}` : "Focus: none",
    `Decisions logged: ${state.decisions.length}`,
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "iaa-desk-brief.txt";
  a.click();
  URL.revokeObjectURL(url);
}

document.addEventListener("DOMContentLoaded", () => {
  $("#ask-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = answerQuestion($("#ask-input").value);
    showToast(answer);
  });

  $("#event-tbody").addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-id]");
    if (row) selectEvent(row.dataset.id);
  });

  $("#filter-ticker").addEventListener("input", renderTable);
  $("#filter-direction").addEventListener("change", renderTable);

  document.querySelectorAll("[data-decision]").forEach((button) => {
    button.addEventListener("click", () => {
      const decision = button.dataset.decision;
      const entry = {
        at: new Date().toISOString(),
        decision,
        event_id: state.selectedId,
        ai: state.desk.verdict.strategy_edge_validated ? "REVIEW" : "NO_TRADE",
      };
      state.decisions.push(entry);
      showToast(`Logged ${decision} for ${state.selectedId || "desk"} — not sent to exchange.`);
    });
  });

  $("#btn-export").addEventListener("click", exportBrief);

  loadDesk().catch((error) => {
    $("#verdict-title").textContent = "Load failed";
    $("#verdict-body").textContent = String(error.message || error);
  });
});

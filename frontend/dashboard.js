const API = window.API_BASE;

async function loadAnalytics() {
  let d;
  try {
    d = await (await fetch(`${API}/analytics`)).json();
  } catch (e) {
    document.getElementById("cards").innerHTML =
      `<div class="card"><div class="value">—</div><div class="label">Backend unreachable (${API})</div></div>`;
    return;
  }

  // --- Usage & resolution KPIs ---
  document.getElementById("cards").innerHTML = `
    ${card(d.total_conversations, "Conversations")}
    ${card(d.resolution_rate + "%", "Resolution Rate", "green")}
    ${card(d.fallback_rate + "%", "Fallback Rate", warn(d.fallback_rate))}
    ${card(d.escalation_rate + "%", "Escalation Rate")}
    ${card(csatDisplay(d), "CSAT", "green")}
    ${card(d.avg_resolution_time_display || "—", "Avg Resolution Time", "blue")}
    ${card(pctOrDash(d.avg_confidence), "Avg Confidence", "blue")}
    ${card(d.kb_hit_rate + "%", "KB Hit Rate")}
  `;

  // --- Business outcomes ---
  const bo = d.business_outcomes || {};
  document.getElementById("outcomes").innerHTML = `
    ${card(bo.contacts_deflected ?? 0, "Contacts Deflected", "green")}
    ${card("$" + fmt(bo.estimated_cost_saved_usd), "Est. Cost Saved", "green")}
    ${card(fmt(bo.estimated_hours_saved) + " h", "Est. Hours Saved", "blue")}
  `;
  const a = (bo.assumptions || {});
  document.getElementById("assumptions").textContent = a.cost_per_human_contact_usd != null
    ? `Assumes $${a.cost_per_human_contact_usd} and ${a.minutes_per_human_contact} min per human-handled contact (configurable).`
    : "";

  // --- Top intents ---
  const intents = d.top_intents || [];
  document.getElementById("intents").innerHTML = intents.length
    ? intents.map(barRow).join("")
    : "<p class='empty'>No data yet — chat with the assistant first.</p>";

  // --- Escalation queue (tickets) ---
  const queue = d.escalation_queue || [];
  document.getElementById("queue").innerHTML = queue.length
    ? queue.map((t) => `<div class="row">
        <span>#${t.id} ${escapeHtml(t.name || "")} <em>${escapeHtml(t.email || "")}</em><br/>${escapeHtml(t.issue || "")}</span>
        <span class="status ${t.status}">${t.status}</span>
      </div>`).join("")
    : "<p class='empty'>No escalations yet. Say “talk to a human” in the chat.</p>";

  // --- Recent conversations ---
  const recent = d.recent_messages || [];
  document.getElementById("recent").innerHTML = recent.length
    ? recent.map((r) => `<div class="row">
        <span>${escapeHtml(r.user_message || "")}</span>
        <span>${r.escalated ? "⤴ escalated" : (r.is_fallback ? "↯ fallback" : (r.intent || ""))}</span>
      </div>`).join("")
    : "<p class='empty'>No conversations yet.</p>";
}

function card(value, label, cls = "") {
  return `<div class="card"><div class="value ${cls}">${value}</div><div class="label">${label}</div></div>`;
}
function barRow(i) {
  return `<div class="bar-row">
    <div class="bar-top"><span>${i.intent}</span><span>${i.percent}% (${i.count})</span></div>
    <div class="bar"><span style="width:${i.percent}%"></span></div>
  </div>`;
}
function warn(v) { return v >= 30 ? "amber" : ""; }
function csatDisplay(d) { return d.responses_rated ? d.csat + "%" : "—"; }
function pctOrDash(v) { return v ? Math.round(v * 100) + "%" : "—"; }
function fmt(n) { return (n ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 }); }
function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

loadAnalytics();
setInterval(loadAnalytics, 15000);

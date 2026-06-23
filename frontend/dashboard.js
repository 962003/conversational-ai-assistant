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

  document.getElementById("cards").innerHTML = `
    ${card(d.total_conversations, "Total Conversations")}
    ${card(d.resolved_conversations, "Resolved", "green")}
    ${card(d.escalations, "Escalations")}
    ${card(d.containment_rate + "%", "Containment Rate", "blue")}
    ${card(d.knowledge_base_hits, "KB Hits")}
    ${card(d.tickets_created, "Tickets")}
  `;

  const intents = d.top_intents || [];
  document.getElementById("intents").innerHTML = intents.length
    ? intents.map(barRow).join("")
    : "<p style='color:var(--muted)'>No data yet — chat with the assistant first.</p>";

  const recent = d.recent_messages || [];
  document.getElementById("recent").innerHTML = recent.length
    ? recent
        .map(
          (r) => `<div class="row">
            <span>${escapeHtml(r.user_message || "")}</span>
            <span>${r.escalated ? "⤴ escalated" : r.intent || ""}</span>
          </div>`
        )
        .join("")
    : "<p style='color:var(--muted)'>No conversations yet.</p>";
}

function card(value, label, cls = "") {
  return `<div class="card"><div class="value ${cls}">${value}</div><div class="label">${label}</div></div>`;
}

function barRow(i) {
  return `<div class="bar-row">
    <div class="bar-top"><span>${i.intent}</span><span>${i.percent}%</span></div>
    <div class="bar"><span style="width:${i.percent}%"></span></div>
  </div>`;
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

loadAnalytics();
setInterval(loadAnalytics, 15000);

const API = window.API_BASE;
const SESSION = "web-" + Math.abs(hashCode(navigator.userAgent + Date.now()));

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("input");
const metaEl = document.getElementById("meta");
const suggestionsEl = document.getElementById("suggestions");
const modal = document.getElementById("ticket-modal");
const modeToggle = document.getElementById("mode-toggle");
const cxStateEl = document.getElementById("cx-state");

let mode = "direct"; // "direct" -> /chat ; "cx" -> /cx/detect-intent

// Reflect whether a real Dialogflow CX agent is wired up.
fetch(`${API}/cx/status`)
  .then((r) => r.json())
  .then((s) => {
    if (s.cx_enabled) {
      cxStateEl.textContent = "● CX agent connected";
      cxStateEl.className = "cx-state on";
    } else {
      cxStateEl.textContent = "● CX not configured (will fall back)";
      cxStateEl.className = "cx-state off";
    }
  })
  .catch(() => {});

modeToggle.addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  mode = e.target.dataset.mode;
  [...modeToggle.children].forEach((b) => b.classList.toggle("active", b === e.target));
});

function hashCode(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}

function addMessage(text, who, tag) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  let html = "";
  if (tag) html += `<span class="tag">${tag}</span>`;
  html += formatMarkdown(text);
  div.innerHTML = html;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function formatMarkdown(t) {
  return t
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/_(.+?)_/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
}

function renderMeta(data) {
  const srcList = data.sources || [];
  const sources = srcList.length
    ? srcList.map((s) => `<span class="pill">${s.doc}${s.score != null ? ` (${s.score})` : ""}</span>`).join(" ")
    : (typeof data.sources === "string" ? data.sources : "—");
  const sClass = data.sentiment === "negative" ? "neg" : data.sentiment === "positive" ? "pos" : "";
  const method = (srcList[0] || {}).method;
  const conf = data.confidence != null ? `${Math.round(data.confidence * 100)}% (${data.confidence_label || "—"})` : "—";
  metaEl.innerHTML = `
    <div><b>Path:</b> <span class="pill">${data.via || mode}</span></div>
    <div><b>Intent:</b> <span class="pill">${data.intent || "—"}</span></div>
    <div><b>Confidence:</b> <span class="pill">${conf}</span></div>
    <div><b>KB hit:</b> <span class="pill">${data.kb_hit ? "yes" : "no"}</span></div>
    ${method ? `<div><b>Retrieval:</b> <span class="pill">${method}</span></div>` : ""}
    <div><b>Sentiment:</b> <span class="pill ${sClass}">${data.sentiment || "—"}</span></div>
    <div style="margin-top:8px"><b>Sources:</b><br/>${sources}</div>`;
}

async function sendMessage(text) {
  addMessage(text, "user");
  const typing = addMessage("Assistant is thinking…", "bot");
  typing.classList.add("typing");
  try {
    let data;
    if (mode === "cx") {
      const res = await fetch(`${API}/cx/detect-intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: SESSION }),
      });
      data = await res.json();
      if (data.cx_enabled === false) {
        // CX not wired up — fall back to the direct pipeline transparently.
        typing.remove();
        addMessage("ℹ️ " + data.message, "bot", "cx fallback");
        return sendDirect(text);
      }
      if (data.error) {
        typing.remove();
        addMessage("⚠️ Dialogflow CX error: " + data.error, "bot");
        return;
      }
      data.via = "dialogflow-cx";
    } else {
      data = await (await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: SESSION }),
      })).json();
    }
    typing.remove();
    addMessage(data.response, "bot", (data.via || mode) + (data.intent ? " · " + data.intent : ""));
    renderMeta(data);
    if (data.escalated) setTimeout(() => openTicketModal(), 400);
  } catch (e) {
    typing.remove();
    addMessage("⚠️ Could not reach the backend. Is the API running at " + API + "?", "bot");
  }
}

async function sendDirect(text) {
  const typing = addMessage("Assistant is thinking…", "bot");
  typing.classList.add("typing");
  const data = await (await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, session_id: SESSION }),
  })).json();
  typing.remove();
  addMessage(data.response, "bot", "direct" + (data.intent ? " · " + data.intent : ""));
  renderMeta(data);
  if (data.escalated) setTimeout(() => openTicketModal(), 400);
}

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendMessage(text);
});

suggestionsEl.addEventListener("click", (e) => {
  if (e.target.tagName === "BUTTON") sendMessage(e.target.textContent);
});

// --- Ticket modal ---
function openTicketModal() { modal.classList.remove("hidden"); }
document.getElementById("t-cancel").onclick = () => modal.classList.add("hidden");
document.getElementById("t-submit").onclick = async () => {
  const name = document.getElementById("t-name").value.trim();
  const email = document.getElementById("t-email").value.trim();
  const issue = document.getElementById("t-issue").value.trim();
  if (!name || !email) return;
  const res = await fetch(`${API}/ticket`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: SESSION, name, email, issue }),
  });
  const data = await res.json();
  modal.classList.add("hidden");
  addMessage(data.message, "bot", "ticket created");
};

// Greeting
addMessage(
  "Hi! I'm the Acme Support Assistant. Ask me about **orders**, **refunds**, **pricing**, or **products** — or say _talk to a human_.",
  "bot",
  "welcome"
);

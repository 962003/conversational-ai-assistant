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

// ---------------------------------------------------------------------------
// Voice AI — browser voicebot via the Web Speech API
//   Speech-to-text (SpeechRecognition) for input, text-to-speech
//   (speechSynthesis) for spoken replies. Production voice would use the
//   Google CCAI telephony connector; this proves the conversation is voice-ready.
// ---------------------------------------------------------------------------
const micBtn = document.getElementById("mic");
const speakToggle = document.getElementById("speak-toggle");
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
let listening = false;

if (!SpeechRec) {
  micBtn.disabled = true;
  micBtn.title = "Voice input not supported in this browser (try Chrome)";
} else {
  recognizer = new SpeechRec();
  recognizer.lang = "en-US";
  recognizer.interimResults = false;
  recognizer.maxAlternatives = 1;

  recognizer.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    inputEl.value = transcript;
    stopListening();
    sendMessage(transcript, { spoken: true }); // auto-speak the reply to a spoken question
  };
  recognizer.onerror = () => stopListening();
  recognizer.onend = () => stopListening();
}

function startListening() {
  if (!recognizer || listening) return;
  listening = true;
  micBtn.classList.add("listening");
  micBtn.textContent = "⏺️";
  try { recognizer.start(); } catch (_) { stopListening(); }
}
function stopListening() {
  listening = false;
  micBtn.classList.remove("listening");
  micBtn.textContent = "🎙️";
}
micBtn.addEventListener("click", () => (listening ? recognizer.stop() : startListening()));

function speak(text) {
  if (!window.speechSynthesis) return;
  // Strip markdown so the spoken version sounds natural.
  const clean = text.replace(/[*_`#>|]/g, "").replace(/\s+/g, " ").trim();
  const u = new SpeechSynthesisUtterance(clean);
  u.lang = "en-US";
  u.rate = 1.02;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

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

function finishBotTurn(data, label, opts) {
  const el = addMessage(data.response, "bot", label);
  attachFeedback(el);
  renderMeta(data);
  if (opts.spoken || speakToggle.checked) speak(data.response);
  if (data.escalated) setTimeout(() => openTicketModal(), 400);
}

async function sendMessage(text, opts = {}) {
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
        return sendDirect(text, opts);
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
    finishBotTurn(data, (data.via || mode) + (data.intent ? " · " + data.intent : ""), opts);
  } catch (e) {
    typing.remove();
    addMessage("⚠️ Could not reach the backend. Is the API running at " + API + "?", "bot");
  }
}

async function sendDirect(text, opts = {}) {
  const typing = addMessage("Assistant is thinking…", "bot");
  typing.classList.add("typing");
  const data = await (await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, session_id: SESSION }),
  })).json();
  typing.remove();
  finishBotTurn(data, "direct" + (data.intent ? " · " + data.intent : ""), opts);
}

// Thumbs up/down feedback → POST /feedback (drives the CSAT metric).
function attachFeedback(msgEl) {
  const bar = document.createElement("div");
  bar.className = "feedback";
  bar.innerHTML = `<span>Helpful?</span>
    <button data-r="1" aria-label="Yes">👍</button>
    <button data-r="0" aria-label="No">👎</button>`;
  bar.addEventListener("click", async (e) => {
    if (e.target.tagName !== "BUTTON") return;
    await fetch(`${API}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: SESSION, rating: Number(e.target.dataset.r) }),
    }).catch(() => {});
    bar.innerHTML = "<span>Thanks for the feedback!</span>";
  });
  msgEl.appendChild(bar);
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

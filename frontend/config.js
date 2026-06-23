// Point this at your deployed FastAPI backend. For local dev it defaults to :8000.
window.API_BASE =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "https://YOUR-BACKEND-URL.onrender.com";

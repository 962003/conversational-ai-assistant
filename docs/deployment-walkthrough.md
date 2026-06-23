# Deployment Walkthrough

A delivery runbook: stand up the full **User → Dialogflow CX → Webhook → FastAPI →
Vertex AI → Gemini** solution on Google Cloud. ~30–45 min.

## Prerequisites
- A Google Cloud project with billing.
- `gcloud` CLI authenticated; `gcloud auth application-default login`.
- APIs enabled:
  ```bash
  gcloud services enable dialogflow.googleapis.com run.googleapis.com \
      aiplatform.googleapis.com cloudbuild.googleapis.com
  ```

## Step 1 — Deploy the backend to Cloud Run
From the repo root (builds `./Dockerfile`, which bundles the knowledge base):
```bash
gcloud run deploy acme-support-ai \
  --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash \
  --set-env-vars USE_VERTEX=true \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project) \
  --set-env-vars GOOGLE_CLOUD_LOCATION=us-central1
```
Copy the service URL, e.g. `https://acme-support-ai-XXXX.run.app`.
Verify: `curl https://.../health` → `retrieval_method`, `embeddings_backend`, etc.

> For an API-key setup instead of Vertex AI: set `GEMINI_API_KEY` (store it in
> **Secret Manager** and pass `--set-secrets GEMINI_API_KEY=gemini-key:latest`).

## Step 2 — Provision the Dialogflow CX agent (as code)
```bash
pip install google-cloud-dialogflow-cx
python dialogflow/provision_agent.py \
  --project YOUR_PROJECT --location global \
  --agent-name "Acme Support AI" \
  --webhook-url https://acme-support-ai-XXXX.run.app/dialogflow/webhook \
  --webhook-secret "$WEBHOOK_SECRET"
```
This creates intents, entities, the **slot-filling pages** (order lookup, handoff),
routes, the no-match fallback, and registers the webhook. It prints the
`DIALOGFLOW_AGENT_ID`.

## Step 3 — Point the backend at the agent
Redeploy (or set env) so `/cx/detect-intent` can drive the agent:
```bash
gcloud run services update acme-support-ai --region us-central1 \
  --set-env-vars DIALOGFLOW_PROJECT=YOUR_PROJECT \
  --set-env-vars DIALOGFLOW_LOCATION=global \
  --set-env-vars DIALOGFLOW_AGENT_ID=THE_PRINTED_ID
```
Verify: `curl https://.../cx/status` → `{"cx_enabled": true, ...}`.

## Step 4 — Frontend
Set `frontend/config.js` `API_BASE` to the Cloud Run URL and deploy the static
files (Vercel/Netlify/any CDN). The chat UI's **Dialogflow CX** toggle now drives
the live agent; the **🎙️ mic** enables the browser voicebot.

## Step 5 — Verify the full path
1. CX **simulator**: "Where is my order 12345?" → matches `order_status`, slot-fills
   `order_id`, calls the webhook, returns grounded shipping info.
2. "I want a human" → handoff page collects name/email/issue → ticket created.
3. Open the **analytics dashboard** → containment, escalation, CSAT, resolution time.

## Step 6 — CI/CD
- `.github/workflows/ci.yml` runs tests on every push/PR.
- `.github/workflows/deploy-cloud-run.yml` (manual dispatch) redeploys; set repo
  secrets `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY`, `GEMINI_API_KEY`.

## Rollback
```bash
gcloud run revisions list --service acme-support-ai --region us-central1
gcloud run services update-traffic acme-support-ai --region us-central1 \
  --to-revisions PREVIOUS_REVISION=100
```

## Production hardening checklist
- [ ] `WEBHOOK_SECRET` set on both the webhook and the CX webhook header
- [ ] Secrets in Secret Manager (not env literals)
- [ ] Move analytics from SQLite → Cloud SQL / BigQuery
- [ ] Vertex AI Vector Search for large knowledge bases
- [ ] CCAI telephony connector for the voice channel

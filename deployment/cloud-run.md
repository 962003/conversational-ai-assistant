# Deploy backend to Google Cloud Run

Cloud Run is the most "on-brand" target for a Google CCAI demo.

```bash
# From the repo root
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build & deploy from the repo ROOT (uses ./Dockerfile, which bundles the KB)
gcloud run deploy acme-support-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_MODEL=gemini-2.5-flash \
  --set-env-vars GEMINI_API_KEY=YOUR_KEY
```

Then point the Dialogflow CX webhook URL at the Cloud Run service URL +
`/dialogflow/webhook`, and update `frontend/config.js` with the same base URL.

> Tip: For production, store `GEMINI_API_KEY` in **Secret Manager** and reference
> it with `--set-secrets GEMINI_API_KEY=gemini-key:latest`, or use **Vertex AI**
> with the service account instead of an API key.

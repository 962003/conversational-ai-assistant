# Dialogflow CX Setup Guide

This folder contains everything needed to reproduce the **Dialogflow CX** side of
the assistant. The CX agent handles **intent detection** and **entity extraction**,
then calls our **FastAPI webhook**, which does **knowledge retrieval + Gemini
grounding** and returns the answer.

```
User → Dialogflow CX (intent + entities) → Webhook (FastAPI) → KB + Gemini → CX → User
```

## ⚡ Fast path: provision the whole agent as code

Instead of clicking through the console, run the provisioning script — it creates
the agent, entity types, intents (with annotated parameters), the fulfillment
webhook, and the Start-Flow routes in one shot:

```bash
pip install google-cloud-dialogflow-cx
gcloud auth application-default login          # or set GOOGLE_APPLICATION_CREDENTIALS

python dialogflow/provision_agent.py \
  --project YOUR_PROJECT_ID \
  --location global \
  --agent-name "Acme Support AI" \
  --webhook-url https://YOUR-BACKEND/dialogflow/webhook \
  --webhook-secret "$WEBHOOK_SECRET"           # optional
```

It prints the new `DIALOGFLOW_AGENT_ID`. Put the project/location/agent id into
`backend/.env`, then the backend can drive the agent via `POST /cx/detect-intent`
(and the frontend's **Dialogflow CX** toggle lights up).

The rest of this doc is the **manual** console equivalent.

---

## 1. Create the agent
1. Open the [Dialogflow CX console](https://dialogflow.cloud.google.com/cx).
2. Create an agent: **"Acme Support AI"**, region `global`, default language `en`.

## 2. Create entity types
Under **Manage → Entity Types**, create the types in
[`agent_export/entities.json`](agent_export/entities.json):
- `order_number` — Regexp `[0-9]{4,7}`
- `email` — Regexp email pattern
- `product_name` — Map with synonyms for the 4 Acme products

## 3. Create intents
Under **Manage → Intents**, create the 6 intents from
[`agent_export/intents.json`](agent_export/intents.json) and paste each set of
training phrases. Annotate `order_id`, `product`, `email`, `person_name`
parameters using the entity types above.

| Intent | Purpose |
|--------|---------|
| `order_status` | Track / look up an order |
| `refund_policy` | Refunds & returns |
| `pricing` | Plans & billing |
| `product_information` | Product & feature questions |
| `human_agent` | Escalate to a person |
| `general_question` | Catch-all → KB |

## 4. Configure the webhook
1. Go to **Manage → Webhooks → Create**.
2. **Name**: `kb-gemini-webhook`
3. **URL**: `https://YOUR-BACKEND-URL/dialogflow/webhook`
4. (Optional) Add header `X-Webhook-Secret: <your secret>` to match
   `WEBHOOK_SECRET` in the backend `.env`.
5. Timeout: 10s.

## 5. Wire fulfillment in the Default Start Flow
For each intent route on the **Start Page** (or a dedicated page per intent):
1. Add a **route** with the intent.
2. Under **Fulfillment → Webhook settings**, enable the webhook and set a **tag**:
   - All KB intents → tag `kb_search`
   - `human_agent` → tag `create_ticket`
3. Leave the static response empty — the webhook supplies the message.

The webhook reads:
- `text` / `transcript` — the user utterance
- `intentInfo.displayName` — the matched intent (mapped to internal keys)
- `sessionInfo.parameters` — `person_name`, `email`, `issue` for ticketing
- `fulfillmentInfo.tag` — `kb_search` vs `create_ticket`

And returns a `fulfillmentResponse` with the grounded answer plus
`sessionInfo.parameters` (`detected_intent`, `kb_hit`, `sentiment`).

## 6. Human handoff page (optional)
For `human_agent`, build a page that collects `person_name`, `email`, and `issue`
via **form parameters**, then calls the webhook with tag `create_ticket`. The
backend creates a ticket and returns a confirmation with the ticket number.

## 7. Test
Use the CX **simulator**: "Where is my order 12345?" → it should match
`order_status`, extract `order_id=12345`, call the webhook, and reply with grounded
shipping info.

## Conversational design (intent roles)

The agent is a full conversation, not just Q&A. The intents map to standard
conversational roles:

| Role | Implemented by | Fulfillment |
|------|----------------|-------------|
| **Greeting** | `Default Welcome Intent` (built-in) | static welcome |
| **Ask a question / Search KB** | `general_question` + the 4 topic intents | webhook tag `kb_search` → KB + Gemini |
| **Escalate to human** | `human_agent` | webhook tag `create_ticket` → ticket |
| **Fallback** | Start Page **no-match** event handler (built-in) | reprompt / offer human |

## Driving CX from the backend (the full path)

Once `DIALOGFLOW_*` are set in `backend/.env`, the app routes a message through
the real agent:

```
POST /cx/detect-intent   { "message": "What is your refund policy?", "session_id": "u1" }
        │
        ▼  Sessions.detect_intent (CX NLU)
   Dialogflow CX ──webhook──▶ POST /dialogflow/webhook ──▶ KB + Gemini
        │
        ◀── answer + sources + confidence (session parameters)
```

`GET /cx/status` reports whether CX is configured. The frontend's **Dialogflow
CX** toggle uses these endpoints and falls back to `/chat` if CX is unset.

## Local testing without CX
You can exercise the exact webhook contract locally:

```bash
curl -X POST http://localhost:8000/dialogflow/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is your refund policy?",
    "intentInfo": {"displayName": "refund_policy"},
    "sessionInfo": {"session": "projects/p/locations/global/agents/a/sessions/demo123"},
    "fulfillmentInfo": {"tag": "kb_search"}
  }'
```

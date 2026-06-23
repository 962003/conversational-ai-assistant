# Architecture

## Overview
A mini Google Contact Center AI: Dialogflow CX understands the user, a FastAPI
webhook retrieves knowledge and grounds an answer with Gemini, and every turn is
logged for analytics.

## End-to-end flow
```
                 ┌─────────────────────────────────────────────────────┐
                 │                       USER                          │
                 │        (Web chat widget / phone / mobile)           │
                 └───────────────────────┬─────────────────────────────┘
                                         │ utterance
                                         ▼
                 ┌─────────────────────────────────────────────────────┐
                 │                 DIALOGFLOW CX                       │
                 │  • NLU: intent detection                            │
                 │  • Entity extraction (order_id, product, email)     │
                 │  • Flows / Pages / Routes                           │
                 └───────────────────────┬─────────────────────────────┘
                                         │ WebhookRequest (intent, params, text)
                                         ▼
                 ┌─────────────────────────────────────────────────────┐
                 │              WEBHOOK — FastAPI backend              │
                 │  /dialogflow/webhook  /chat  /knowledge/search       │
                 │  /analytics  /ticket                                │
                 └───────┬─────────────────────────────────┬───────────┘
                         │                                 │
                         ▼                                 ▼
        ┌────────────────────────────┐      ┌──────────────────────────────┐
        │      KNOWLEDGE BASE        │      │            GEMINI            │
        │  *.md → sectioned chunks   │─────▶│  gemini-2.5-flash            │
        │  TF-IDF keyword retrieval  │ ctx  │  grounded, context-only answer│
        └────────────────────────────┘      └──────────────┬───────────────┘
                         │                                 │ answer
                         ▼                                 │
        ┌────────────────────────────┐                    │
        │     ANALYTICS (SQLite)     │◀───────────────────┘
        │  intents, KB hits,         │  log every turn
        │  escalations, sentiment    │
        └────────────────────────────┘
                                         │ WebhookResponse (message + params)
                                         ▼
                                       USER
```

## Components

| Layer | Tech | Responsibility |
|-------|------|----------------|
| NLU | Dialogflow CX | Intent + entity detection, conversation state |
| CX agent (as code) | `dialogflow/provision_agent.py` | Creates agent, entities, intents, webhook, Start-Flow routes via the CX SDK |
| CX client | `app/cx_client.py` + `app/routers/cx.py` | `detect_intent` → routes a message through the real CX agent (`/cx/detect-intent`) |
| Webhook | FastAPI (`app/routers/webhook.py`) | Parse CX request, orchestrate, return answer + sources + confidence |
| Orchestration | `app/service.py` | intent → retrieve → ground → log |
| Embeddings | `app/embeddings.py` | Vertex AI / Gemini text embeddings (one SDK, both backends) |
| Retrieval | `app/knowledge_base.py` | Markdown → chunks → vector search (TF-IDF fallback) |
| LLM | `app/gemini_client.py` | Grounded answers, intent & sentiment fallback |
| Analytics | `app/analytics.py` + SQLite | Aggregate metrics for the dashboard |
| Frontend | Static HTML/CSS/JS | Chat widget + analytics dashboard |

## Design decisions
- **Grounded generation.** Gemini is instructed to answer **only** from retrieved
  context and to refuse + offer human handoff when the answer is absent. This is
  the anti-hallucination guarantee enterprises require.
- **Graceful degradation.** With no `GEMINI_API_KEY`, the app still runs using
  keyword intent detection and extractive answers — so it demos in CI/offline.
- **Two entry points, one pipeline.** `/dialogflow/webhook` (for CX) and `/chat`
  (for the web widget) both call `service.handle_turn`, guaranteeing identical
  behavior whether or not CX is in the loop.
- **The CX path is real, not just claimed.** `/cx/detect-intent` calls a live CX
  agent (provisioned by `provision_agent.py`); CX then calls our webhook for
  fulfillment. The frontend has a **Direct vs Dialogflow CX** toggle, so the full
  `User → CX → Webhook → KB → Gemini` path is demonstrable end-to-end. If CX isn't
  configured the endpoint reports `cx_enabled: false` and the UI falls back to
  `/chat` — no broken demo.
- **Answer + sources + confidence.** Every turn returns a grounded answer, the KB
  sources it used, and a 0–1 confidence (top retrieval score; vector cosine, or a
  squashed TF-IDF score in fallback). The webhook passes these back to CX as both
  a custom payload and session parameters.
- **Vector retrieval with graceful fallback.** Retrieval embeds KB chunks with
  **Vertex AI / Gemini** (`text-embedding-004`) and ranks by cosine similarity.
  Document vs. query inputs use asymmetric task types (`RETRIEVAL_DOCUMENT` /
  `RETRIEVAL_QUERY`) for better recall. Chunk embeddings are cached to disk keyed
  by a content+model signature, so the embedding API is called only when the KB or
  model changes. If no credentials are present, `knowledge_base.py` transparently
  falls back to TF-IDF — same `search()` interface, no other code changes.

## Upgrade path to full CCAI
- ✅ **Vertex AI / Gemini embeddings** for vector retrieval (done — see
  `app/embeddings.py`). Next: move the in-memory cosine index to **Vertex AI
  Vector Search** for large corpora.
- Use **Vertex AI Gemini** generation with service-account auth (`USE_VERTEX=true`)
  instead of an API key.
- Add **CCAI telephony** (Acme Voice Gateway) for voice.
- Move tickets to a real CRM via **Acme Connectors** (Zendesk/Salesforce).
- Stream analytics to **BigQuery** + Looker Studio.

# Solution Architecture

> A production-shaped **Conversational AI solution** for enterprise customer
> support — Google **Dialogflow CX** for conversation, a **FastAPI** fulfillment
> webhook, **Vertex AI embeddings** for retrieval, and **Gemini** for grounded
> generation. A mini Google Contact Center AI.

## Executive summary

Enterprises field the same questions thousands of times a day. This solution
**contains** those conversations with an AI assistant that understands intent,
retrieves the right policy from an approved knowledge base, and answers in natural
language — **grounded** (no hallucinations) with a **confidence score**, and
**escalates to a human** when it should. Every turn is measured for analytics.

The architecture is **vertical-agnostic**: swap the knowledge base and the same
platform serves Support, HR, Legal, or Enterprise Search (see
[Business Impact](business-impact.md)).

## Request flow

```
        Customer
           │  "What's your refund policy?"
           ▼
   ┌─────────────────┐
   │  Dialogflow CX  │   NLU: intent + entity detection, conversation state
   └────────┬────────┘
            │  WebhookRequest (intent, parameters, text, session)
            ▼
   ┌─────────────────┐
   │     Webhook     │   /dialogflow/webhook — validate, parse, route by tag
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │     FastAPI     │   orchestration: service.handle_turn()
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ Knowledge Base  │   Markdown → sectioned chunks
   └────────┬────────┘
            ▼
   ┌──────────────────────┐
   │ Vertex AI Embeddings │   embed query + chunks → cosine top-k  (TF-IDF fallback)
   └────────┬─────────────┘
            ▼
   ┌─────────────────┐
   │     Gemini      │   grounded generation from retrieved context only
   └────────┬────────┘
            ▼
        Response          answer + sources + confidence
           │
           ▼
        Customer
```

## Layered view

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │ CHANNELS        Web chat · (CCAI telephony / mobile — roadmap)         │
 ├──────────────────────────────────────────────────────────────────────┤
 │ CONVERSATION    Dialogflow CX  — agent, flows, pages, intents,         │
 │                 entities, routes, fulfillment (provisioned as code)    │
 ├──────────────────────────────────────────────────────────────────────┤
 │ FULFILLMENT     FastAPI webhook  — /dialogflow/webhook, /cx/detect-    │
 │                 intent, /chat, /knowledge/search, /ticket, /analytics  │
 ├──────────────────────────────────────────────────────────────────────┤
 │ RETRIEVAL       Knowledge base (Markdown→chunks) + Vertex AI / Gemini  │
 │                 embeddings → cosine search (cached; TF-IDF fallback)   │
 ├──────────────────────────────────────────────────────────────────────┤
 │ GENERATION      Gemini 2.5 Flash — context-only grounded answers       │
 ├──────────────────────────────────────────────────────────────────────┤
 │ DATA / OPS      SQLite (turns, tickets) → analytics; cache; logging    │
 └──────────────────────────────────────────────────────────────────────┘
```

## Sequence (a single grounded turn)

1. **Customer** sends a message to the **Dialogflow CX** agent.
2. **CX** detects the intent (e.g. `refund_policy`) and extracts entities
   (`order_id`, `product`, `email`).
3. CX invokes the **fulfillment webhook** with the intent, parameters, and text.
4. **FastAPI** routes by fulfillment tag (`kb_search` vs `create_ticket`).
5. **Retrieval** embeds the query with **Vertex AI embeddings** and ranks knowledge
   base chunks by cosine similarity (asymmetric `RETRIEVAL_QUERY` /
   `RETRIEVAL_DOCUMENT` task types). Falls back to TF-IDF with no credentials.
6. **Gemini** generates an answer **only** from the retrieved context; if the
   answer isn't present it declines and offers a human.
7. The webhook returns **answer + sources + confidence** to CX (custom payload +
   session parameters); CX replies to the customer.
8. The turn is logged for **analytics** (intent, KB hit, confidence, sentiment,
   escalation).

## Key design decisions

| Decision | Why it matters to a customer |
|----------|------------------------------|
| **Grounded generation** (context-only + refusal) | No hallucinated policies/prices — the enterprise trust requirement. |
| **Confidence on every answer** | Low confidence routes to a human instead of guessing. |
| **Vector retrieval with graceful fallback** | Quality when credentials exist; the demo never breaks without them. |
| **Agent provisioned as code** (`provision_agent.py`) | Reproducible, reviewable, environment-promotable — not console clicks. |
| **One pipeline, two entry points** (`/chat` + `/dialogflow/webhook`) | Identical behavior with or without CX in the loop; testable offline. |
| **Vertical-agnostic KB** | Same platform, new knowledge base → new use case. |

## Non-functional considerations

- **Scalability** — stateless FastAPI behind Cloud Run autoscaling; embeddings
  cached by content+model signature; in-memory cosine index swaps to **Vertex AI
  Vector Search** for large corpora.
- **Security** — webhook shared-secret header; Vertex AI via service-account /
  ADC; secrets in Secret Manager; TLS in transit, encryption at rest.
- **Cost** — Gemini 2.5 Flash + cached embeddings keep per-conversation cost low;
  retrieval limits context tokens; analytics surface containment (deflection)
  to quantify ROI.
- **Observability** — per-turn logging, `/health` (model, retrieval method,
  embeddings backend, CX status), analytics dashboard.

## Deployment topology

```
 Frontend (static)         Backend (FastAPI)            Google Cloud
 ────────────────          ──────────────────           ────────────
 Vercel / Netlify  ──────▶ Cloud Run / Render  ──────▶  Dialogflow CX
                           (Docker, autoscale)          Vertex AI (embeddings, Gemini)
```

See [`deployment/`](../deployment/) (Cloud Run / Render / Railway) and the
[technical architecture](architecture.md) for module-level detail.

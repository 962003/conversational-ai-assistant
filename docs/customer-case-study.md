# Customer Case Study — NorthPeak Retail

> A delivery story in the shape a **Technical Solutions Consultant** tells it:
> **Customer requirement → solution design → deployment → business impact.**
>
> *NorthPeak Retail is an illustrative composite customer used to frame how this
> solution would be delivered in a real engagement. Metrics are modeled; the
> platform that produces them is in this repo.*

## One-line narrative

> *"NorthPeak had a support-cost problem — repetitive tickets were overwhelming a
> small agent team. I ran discovery with their CX and support leads, designed a
> Dialogflow CX + Gemini assistant with grounded answers and human handoff,
> deployed it on Cloud Run, and improved containment while cutting agent workload
> on Tier-1 questions."*

## 1. Customer & requirement

**Customer:** NorthPeak Retail — mid-size e-commerce (≈ 2,500 support contacts/week).

**The problem they brought:**
- 70%+ of contacts were repetitive: *where is my order, refund policy, pricing,
  product questions.*
- Agents were overloaded; response times slipped; after-hours had no coverage.
- A previous FAQ bot **hallucinated policies**, eroding trust — so leadership was
  skeptical of "AI."

**Stated goal:** deflect repetitive contacts **without** wrong answers, and hand
off cleanly to humans for anything else.

## 2. Discovery (workshops & stakeholders)

Activities I'd run in the engagement:
- **Requirements workshop** with Support Ops, CX lead, and IT — mapped the top
  contact drivers and which were "answerable from existing docs."
- **Stakeholder alignment:** Support Ops cared about *deflection*; the CX lead about
  *no hallucinations / brand trust*; IT about *security & deployment*; Finance about
  *ROI*. I framed success metrics for each (see [ROI analysis](roi-analysis.md)).
- **Content audit:** identified the source-of-truth docs (refund, shipping, pricing,
  products, FAQ) that became the **knowledge base**.
- **Journey mapping:** defined the conversation flows, required slots, and the
  escalation path (see [customer-journey-design.md](customer-journey-design.md)).

**Key requirement that shaped the design:** *answers must be grounded in approved
content, with a confident handoff when the bot isn't sure.*

## 3. Solution design

A mini **Google Contact Center AI** ([solution-architecture.md](solution-architecture.md)):

```
Customer → Dialogflow CX (intents + slot filling) → Webhook (FastAPI)
        → Knowledge Base → Vertex AI Embeddings → Gemini (grounded) → response
        → human handoff + ticket when needed
```

Design decisions tied back to stakeholder concerns:
- **Grounded generation** (context-only + refusal) → solved the *hallucination/trust*
  concern that sank the previous bot.
- **Confidence + fallback → human handoff** → protected CX quality.
- **Dialogflow CX** (intents, entities, pages, slot filling) → natural multi-turn
  flows (e.g., collecting an order number).
- **Cloud Run + Vertex AI** → fit IT's Google Cloud standards and security posture.

## 4. Implementation

- Modeled **6 intents** + entities (order number, email, product) — provisioned as
  code ([provision_agent.py](../dialogflow/provision_agent.py)).
- Built **slot-filling pages** (order lookup; handoff collecting name/email/issue).
- Implemented the **webhook fulfillment** returning answer + sources + confidence.
- Wired **human handoff → ticket** with the escalation queue.
- Added a **voice channel** (browser voicebot; CCAI telephony as the production path).
- Stood up **analytics** (containment, escalation, fallback, CSAT, resolution time).

## 5. Deployment

- Containerized backend → **Cloud Run** (autoscaling); static chat UI to the CDN.
- **CI/CD**: GitHub Actions runs tests on every push; manual Cloud Run deploy.
- Connected the **Dialogflow CX webhook** to the Cloud Run URL; secrets in Secret
  Manager. Full runbook: [deployment-walkthrough.md](deployment-walkthrough.md).

## 6. Business impact

Measured on the live analytics dashboard (illustrative targets for NorthPeak):

| Metric | Before | After | 
|--------|--------|-------|
| Containment (resolution) rate | — | **~70%** of repetitive contacts |
| Tier-1 agent workload | 100% | **−60%** on repetitive intents |
| After-hours coverage | none | **24/7** |
| Wrong-answer incidents | recurring | **~0** (grounded + refusal) |
| CSAT on AI-handled chats | — | tracked via 👍/👎 feedback |

Estimated savings and payback are modeled in [ROI analysis](roi-analysis.md).

## 7. Stakeholder management & lessons

- **Earned trust incrementally:** demoed the *refusal* behavior first ("it says it
  doesn't know rather than guessing") to win over the skeptical CX lead.
- **Made it measurable:** the dashboard gave Support Ops and Finance a shared,
  honest view of containment and deflected cost.
- **Designed for handoff, not replacement:** positioned the bot as deflecting
  Tier-1 so agents focus on complex, high-value cases — which de-risked adoption
  with the agent team.

## Talking points (interview-ready)

- *Requirement → design → deploy → impact*, in one breath (see the one-liner above).
- "I grounded every answer and added confidence-based handoff to solve the trust
  problem that killed their last bot."
- "I provisioned the CX agent as code so it's reproducible and reviewable."
- "I instrumented containment, escalation, CSAT, and resolution time so we could
  prove ROI — not just ship a bot."

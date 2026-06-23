# Business Impact

> The same platform — Dialogflow CX + Webhook + FastAPI + Knowledge Base + Vertex
> AI embeddings + Gemini — solves a class of expensive enterprise problems:
> **repetitive, knowledge-bound conversations**. Change the knowledge base, serve a
> new department.

## The problem (and what it costs)

Knowledge workers and support agents spend a large share of their time answering
questions whose answers already exist in documents — policies, FAQs, handbooks,
contracts. The cost shows up as:

- **High support volume** and long queues for low-complexity questions.
- **Slow time-to-answer** for employees searching across scattered systems.
- **Inconsistent answers** when humans paraphrase policy from memory.
- **After-hours gaps** — no coverage outside business hours.

## How this solution helps

| Lever | Mechanism | Outcome |
|-------|-----------|---------|
| **Deflection / containment** | AI resolves repetitive questions end-to-end | Fewer tickets reach humans |
| **Faster answers** | Retrieval + grounded generation in seconds | Lower time-to-answer, 24/7 |
| **Consistency & trust** | Context-only answers with sources + confidence | No hallucinated policy; auditable |
| **Smart escalation** | Low confidence / explicit request → human handoff + ticket | Humans focus on complex cases |
| **Measurable ROI** | Analytics: containment rate, top intents, KB hits | Prove value, target content gaps |

> **Illustrative** targets for a mature deployment (calibrate per customer):
> 60–80% containment on repetitive intents, answers in seconds vs. minutes, 24/7
> coverage. The built-in [analytics dashboard](../frontend/dashboard.html) reports
> the **actual** containment rate, escalations, and top intents from live traffic.

## Use cases (one platform, many verticals)

The architecture is **vertical-agnostic** — only the knowledge base and intents
change. Each use case below reuses the identical CX → Webhook → FastAPI →
Embeddings → Gemini pipeline.

### 1. Customer Support  ✅ *(implemented in this repo)*
- **Audience:** customers.
- **Knowledge base:** refund policy, pricing, shipping, products, FAQ.
- **Intents:** order status, refund, pricing, product info, escalate to human.
- **Value:** deflects Tier-1 tickets, 24/7 answers, instant order/policy lookups.

### 2. HR Assistant
- **Audience:** employees.
- **Knowledge base:** leave & PTO policy, benefits, payroll, onboarding, code of
  conduct.
- **Intents:** check leave policy, benefits enrollment, payroll question, IT/HR
  ticket, talk to HR.
- **Value:** frees HR from repetitive questions; consistent policy answers;
  confidential self-service.

### 3. Legal Assistant
- **Audience:** internal teams (sales, procurement, employees).
- **Knowledge base:** contract templates, clause library, NDA/DPA guidance,
  compliance policies.
- **Intents:** clause lookup, contract-process question, compliance check, escalate
  to counsel.
- **Value:** faster contract turnaround; first-line triage; **grounded with
  citations** so guidance is traceable — and explicit handoff for anything that
  needs a lawyer.

### 4. Enterprise Knowledge Search
- **Audience:** all employees.
- **Knowledge base:** wikis, runbooks, product docs, SOPs across teams.
- **Intents:** how-do-I, where-is, who-owns, definition/lookup.
- **Value:** one natural-language entry point across siloed systems; cuts time
  spent hunting for information; surfaces the **source** for every answer.

## Why it generalizes

```
        ┌──────────────────────────────────────────┐
        │   Dialogflow CX → Webhook → FastAPI →     │   ← unchanged platform
        │   Embeddings → Gemini → grounded answer   │
        └──────────────────────────────────────────┘
                 ▲              ▲              ▲
          Support KB        HR KB          Legal KB        ← swap the knowledge base
        + support intents + HR intents   + legal intents   ← swap the intents
```

Standing up a new vertical means: (1) drop in a new `knowledge_base/`, (2) define
its intents in `provision_agent.py`, (3) deploy. The retrieval, grounding,
confidence, escalation, and analytics are reused as-is.

## What to measure (success metrics)

- **Containment / deflection rate** — % of conversations resolved without a human.
- **Escalation rate & reasons** — where the AI hands off (and why).
- **Time-to-answer** — median response latency vs. the human baseline.
- **Coverage / KB-hit rate** — % of questions the knowledge base can answer
  (gaps = content to add).
- **Confidence distribution** — calibrate the human-handoff threshold.
- **CSAT** (roadmap) — satisfaction on AI-handled conversations.

All of the above except CSAT are already produced by the
[analytics dashboard](../frontend/dashboard.html) and `GET /analytics`.

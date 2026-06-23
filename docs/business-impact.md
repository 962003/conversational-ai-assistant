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

### 4. Banking / Financial Services Assistant
- **Audience:** retail banking customers.
- **Knowledge base:** account & card policies, fees, loan/EMI rules, branch/ATM
  info, dispute process.
- **Intents:** balance/transaction question, card block, fees & charges, loan
  eligibility, report fraud → **escalate to a banker**.
- **Value:** 24/7 self-service for high-volume queries; strict **grounding** (no
  invented rates/fees) and instant handoff for anything sensitive (fraud, disputes).

### 5. IT Service Desk
- **Audience:** employees.
- **Knowledge base:** how-to guides, access/VPN, software catalog, known issues,
  SLAs.
- **Intents:** password reset, access request, troubleshoot issue, software
  request, **raise a ticket** to L2.
- **Value:** deflects L1 tickets, faster resolution, consistent runbook answers;
  unresolved cases escalate with full context into the ticket queue.

### 6. Appointment Booking
- **Audience:** customers / patients.
- **Knowledge base:** services, hours, locations, prep instructions, cancellation
  policy.
- **Intents:** check availability, book/reschedule/cancel (slot filling: service,
  date, time, contact), pre-visit questions.
- **Value:** showcases **multi-slot form filling** end-to-end; reduces phone volume
  and no-shows with 24/7 booking and reminders.

### 7. Enterprise Knowledge Search
- **Audience:** all employees.
- **Knowledge base:** wikis, runbooks, product docs, SOPs across teams.
- **Intents:** how-do-I, where-is, who-owns, definition/lookup.
- **Value:** one natural-language entry point across siloed systems; cuts time
  spent hunting for information; surfaces the **source** for every answer.

> These are deliberately **real enterprise workflows** (support, banking, IT,
> scheduling) — not toy bots (weather/movie/FAQ). The harder, higher-value the
> workflow, the more the grounding + slot filling + escalation design matters.

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

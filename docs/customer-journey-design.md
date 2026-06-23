# Conversational & Customer-Journey Design

How the Dialogflow CX agent is *designed as a conversation* — not just a Q&A
endpoint. Everything here is provisioned as code in
[`dialogflow/provision_agent.py`](../dialogflow/provision_agent.py).

## Building blocks (Dialogflow CX)

| Concept | In this agent |
|---------|---------------|
| **Agent** | "Acme Support AI" — one virtual agent, default language `en`. |
| **Intents** | `order_status`, `refund_policy`, `pricing`, `product_information`, `human_agent`, `general_question` + built-in Welcome. |
| **Entities** | `order_number` (regex), `email` (regex), `product_name` (map/synonyms); system `sys.person`, `sys.any`. |
| **Flows** | Default Start Flow holds the routing logic. |
| **Pages** | `Collect Order` and `Human Handoff` — stateful steps with form slot filling. |
| **Routes** | Intent routes (to pages or webhook fulfillment) + condition routes (`$page.params.status = "FINAL"`). |
| **Fallbacks** | `sys.no-match-default` (flow + per-parameter) and `sys.no-input-default` reprompts. |
| **Contexts / state** | Session parameters (`order_id`, `person_name`, `email`, `issue`, plus webhook-set `confidence`, `kb_hit`, `sentiment`). |

## Routing model

```
Start Flow
├─ intent: order_status        → Page "Collect Order"   (slot-fill order_id → webhook kb_search)
├─ intent: human_agent         → Page "Human Handoff"   (slot-fill name/email/issue → webhook create_ticket)
├─ intent: refund_policy       → webhook (kb_search)
├─ intent: pricing             → webhook (kb_search)
├─ intent: product_information → webhook (kb_search)
├─ intent: general_question    → webhook (kb_search)
└─ event: sys.no-match-default → webhook (kb_search)     ← fallback still attempts a grounded answer
```

## Slot filling (multi-turn)

The `Collect Order` page **requires** `order_id` before fulfilling:

```
User:  Where is my order?
Bot:   Sure — what's your order number?          ← initial prompt (parameter not yet filled)
User:  banana                                     ← no-match
Bot:   That doesn't look like an order number (4–7 digits). Please try again.   ← reprompt
User:  12345                                      ← entity extracted → order_id = 12345
Bot:   (status = FINAL) → webhook kb_search → grounded order-status answer
```

`Human Handoff` collects `person_name`, `email`, `issue` the same way, then calls
the webhook with tag `create_ticket` to open a ticket.

## Customer journeys (business workflows)

### Order-status journey
```
greet → ask "where is my order" → [collect order_id w/ reprompts]
      → webhook → KB(shipping) → Gemini → grounded status → (offer more help)
```

### Refund journey
```
ask refund question → intent refund_policy → webhook → KB(refund_policy)
   → Gemini grounded answer → if unresolved → escalate
```

### Escalation / handoff journey  (Bot → Agent)
```
"talk to a human" OR low confidence → Human Handoff page
   → collect name + email + issue → webhook create_ticket
   → ticket # confirmed → appears in the Escalation Queue (analytics dashboard)
```

## Fallback & containment strategy

- **Per-parameter** no-match / no-input reprompts during slot filling.
- **Flow-level** `sys.no-match-default` routes to the KB webhook, so an unmatched
  utterance still gets a grounded attempt instead of a dead end.
- **Grounding guardrail:** if the KB has no answer, Gemini declines and offers a
  human — and low **confidence** can trigger handoff. See
  [solution-architecture.md](solution-architecture.md).

## Voice & Contact Center AI

The same agent + webhook serve voice with no business-logic changes — this is the
**Google Contact Center AI** pattern.

**Implemented now — browser voicebot.** The chat UI includes **speech-to-text**
(mic → transcript → same pipeline) and **text-to-speech** (spoken replies) via the
Web Speech API ([app.js](../frontend/app.js)). You can hold a spoken conversation
with the assistant today — no telephony required.

**Production path (roadmap):**
- **CCAI telephony** connector (or a SIP gateway / the "Acme Voice Gateway" product
  in the KB) bridges phone calls to the CX agent.
- **Speech-to-text / text-to-speech** handled by CX's audio config; barge-in and
  call-transfer map to the handoff page.
- **Agent Assist** can surface the same KB+Gemini answers to live agents.

Status: **voicebot implemented (browser); telephony channel = roadmap.**

## Design principles

1. **Collect before you fulfill** — required slots with graceful reprompts.
2. **Never dead-end** — fallback attempts a grounded answer, then offers a human.
3. **Ground everything** — answers come only from the KB, with sources + confidence.
4. **Escalate with context** — handoff carries name/email/issue into a ticket.
5. **Measure the journey** — every turn logs intent, confidence, fallback, handoff
   for the [analytics dashboard](../frontend/dashboard.html).

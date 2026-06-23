# ROI Analysis

> How a consultant justifies the investment. Numbers are **modeled** with stated
> assumptions; the live [analytics dashboard](../frontend/dashboard.html) reports
> the **actual** containment and deflected-cost figures from real traffic, using
> the same formulas.

## Assumptions (editable)

| Assumption | Value | Notes |
|------------|-------|-------|
| Support contacts / week | 2,500 | NorthPeak baseline |
| Repetitive (automatable) share | 70% | from the content/contact audit |
| Fully-loaded cost per human contact | **$6.00** | `cost_per_human_contact_usd` in config |
| Handling time per human contact | **6 min** | `minutes_per_human_contact` in config |
| Target containment on repetitive contacts | 70% | conservative for a grounded bot |

## Deflection model

```
Repetitive contacts/week      = 2,500 × 70%            = 1,750
Contained by the assistant    = 1,750 × 70%            = 1,225 / week
Agent hours saved/week        = 1,225 × 6 min ÷ 60     ≈ 122 hours
Cost saved/week               = 1,225 × $6.00          = $7,350
Cost saved/year (×52)         ≈ $382,200
```

> The dashboard computes the live version: `contacts_deflected`,
> `estimated_cost_saved_usd`, `estimated_hours_saved` from actual resolved
> conversations (see [analytics.py](../backend/app/analytics.py)).

## Cost side (illustrative)

| Item | Estimate |
|------|----------|
| Gemini 2.5 Flash + embeddings (cached) | low per-conversation cost |
| Cloud Run (autoscale, scale-to-zero) | usage-based |
| Build / delivery (one-time) | engagement cost |

Because per-conversation inference cost is small relative to a **$6** human contact,
the model is dominated by deflection volume — so **payback is fast** once
containment climbs.

## Sensitivity (annual cost saved)

| Containment ↓/↑ | Annual saved (≈) |
|-----------------|------------------|
| 50% | ~$273,000 |
| 70% (base) | ~$382,000 |
| 85% | ~$464,000 |

## What to track to *prove* ROI (live metrics)

- **Containment / resolution rate** — the deflection driver.
- **Escalation rate** — where humans are still needed (and why).
- **Fallback rate** — content gaps to close (raises containment over time).
- **CSAT** — quality guardrail so deflection isn't bought with bad experiences.
- **Avg resolution time** — speed vs. the human baseline.
- **Intent accuracy** — measured against a golden set
  ([intent_eval.py](../backend/eval/intent_eval.py)) so routing quality is provable.

## The consultant's framing

> "For ~$6 per avoided human contact and a small inference cost, containing 1,225
> repetitive contacts/week frees ~122 agent-hours/week and ~$380K/year — while CSAT
> and grounding guardrails keep quality intact. We grow ROI by closing the content
> gaps the **fallback rate** exposes."

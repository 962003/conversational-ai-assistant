"""Intent-detection accuracy evaluation harness.

Measures intent accuracy against a labeled "golden" set — the standard way a
conversational-AI consultant reports NLU quality (vs. eyeballing). Runs against the
project's intent detector (Gemini when a key is set; deterministic keyword
classifier otherwise), so it works in CI with no credentials.

Run:  python -m eval.intent_eval        (from the backend/ directory)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.gemini_client import get_gemini  # noqa: E402

# (utterance, expected_intent) — the labeled evaluation set.
GOLDEN: list[tuple[str, str]] = [
    # order_status
    ("Where is my order 12345?", "order_status"),
    ("Track my order please", "order_status"),
    ("Has my package shipped yet?", "order_status"),
    ("When will my delivery arrive?", "order_status"),
    # refund_policy
    ("What is your refund policy?", "refund_policy"),
    ("I want to return this item", "refund_policy"),
    ("Can I get my money back?", "refund_policy"),
    ("How do refunds work?", "refund_policy"),
    # pricing
    ("How much does the Pro plan cost?", "pricing"),
    ("What is your pricing?", "pricing"),
    ("Do you have a cheaper subscription?", "pricing"),
    ("What's the price of the business plan?", "pricing"),
    # product_information
    ("Tell me about the Acme Voice Gateway product", "product_information"),
    ("What features does this product have?", "product_information"),
    ("What is the SKU for the hub?", "product_information"),
    ("Does the product support integrations?", "product_information"),
    # human_agent
    ("I want to talk to a human", "human_agent"),
    ("Connect me to an agent", "human_agent"),
    ("Can I speak to a representative?", "human_agent"),
    ("Get me a human agent now", "human_agent"),
    # general_question
    ("How do I reset my password?", "general_question"),
    ("Is my data secure?", "general_question"),
    ("What are your support hours?", "general_question"),
    ("How do I change my settings?", "general_question"),
]


def evaluate() -> dict:
    gemini = get_gemini()
    correct = 0
    per_intent_total: dict[str, int] = defaultdict(int)
    per_intent_correct: dict[str, int] = defaultdict(int)
    confusion: list[dict] = []

    for utterance, expected in GOLDEN:
        predicted = gemini.detect_intent(utterance)
        per_intent_total[expected] += 1
        if predicted == expected:
            correct += 1
            per_intent_correct[expected] += 1
        else:
            confusion.append({"utterance": utterance, "expected": expected, "predicted": predicted})

    total = len(GOLDEN)
    return {
        "accuracy": round(correct / total, 3),
        "correct": correct,
        "total": total,
        "classifier": "gemini" if gemini.enabled else "keyword-fallback",
        "per_intent": {
            intent: {
                "accuracy": round(per_intent_correct[intent] / per_intent_total[intent], 3),
                "n": per_intent_total[intent],
            }
            for intent in sorted(per_intent_total)
        },
        "misclassifications": confusion,
    }


def main():
    r = evaluate()
    print(f"Intent accuracy: {r['accuracy']:.1%}  ({r['correct']}/{r['total']})  "
          f"[classifier: {r['classifier']}]")
    print("\nPer-intent:")
    for intent, m in r["per_intent"].items():
        print(f"  {intent:22} {m['accuracy']:.0%}  (n={m['n']})")
    if r["misclassifications"]:
        print("\nMisclassifications:")
        for m in r["misclassifications"]:
            print(f"  '{m['utterance']}' → {m['predicted']} (expected {m['expected']})")


if __name__ == "__main__":
    main()

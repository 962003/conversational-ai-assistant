"""Intent accuracy is measured against a labeled golden set (not eyeballed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.intent_eval import evaluate  # noqa: E402


def test_intent_accuracy_meets_baseline():
    r = evaluate()
    assert r["total"] >= 20
    # Baseline gate so regressions in intent routing fail CI.
    assert r["accuracy"] >= 0.75, f"intent accuracy regressed: {r}"


def test_every_intent_is_covered():
    r = evaluate()
    expected = {"order_status", "refund_policy", "pricing",
                "product_information", "human_agent", "general_question"}
    assert expected <= set(r["per_intent"].keys())

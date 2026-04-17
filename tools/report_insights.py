"""Shared insight validation and dry-run insight generation."""
from __future__ import annotations

REQUIRED_INSIGHT_KEYS = {
    "slide3_general_insights",
    "slide3_budget_roas",
    "slide3_strategy",
    "google_top_performer",
    "google_main_drop",
    "google_next_steps",
    "meta_top_performer",
    "meta_main_drop",
    "meta_next_steps",
    "performance_manager_narrative",
    "action_items",
}


def assert_insights_shape(insights: dict) -> None:
    missing = sorted(REQUIRED_INSIGHT_KEYS - set(insights))
    if missing:
        raise ValueError(f"Claude response is missing required insight keys: {missing}")
    action_items = insights.get("action_items")
    if not isinstance(action_items, list) or len(action_items) < 5:
        raise ValueError("Claude response must include at least 5 action_items.")


def build_fake_insights(kpis: dict, client: str, month: str, year: int, next_month: str) -> dict:
    """Return deterministic dry-run copy for template and API testing."""
    total = kpis["totals"]
    google = kpis["google"]
    meta = kpis["meta"]
    return {
        "slide3_general_insights": (
            f"{client} generated ${total['revenue']:,.2f} from ${total['cost']:,.2f} "
            f"in ad spend during {month} {year}, producing {total['roas']} ROAS."
        ),
        "slide3_budget_roas": (
            f"Google delivered {google['roas']} ROAS and Meta delivered {meta['roas']} ROAS; "
            "prioritize spend toward the stronger marginal return after reviewing funnel capacity."
        ),
        "slide3_strategy": "Use this dry-run narrative only to validate the Slides replacement pipeline.",
        "google_top_performer": f"Google revenue was ${google['revenue']:,.2f} on ${google['cost']:,.2f} spend.",
        "google_main_drop": "Dry-run insight: review campaigns with low ROAS before scaling.",
        "google_next_steps": "Dry-run action: isolate the best funnel and validate search term quality.",
        "meta_top_performer": f"Meta revenue was ${meta['revenue']:,.2f} on ${meta['cost']:,.2f} spend.",
        "meta_main_drop": "Dry-run insight: review creative fatigue and audience overlap.",
        "meta_next_steps": "Dry-run action: refresh creative and rebalance budget by funnel.",
        "performance_manager_narrative": (
            f"Dry-run summary for {client}: validate final language with Claude before client delivery."
        ),
        "action_items": [
            f"Confirm {next_month} budget allocation.",
            "Review top ads by revenue.",
            "Check underperforming funnel stages.",
            "Validate company revenue override.",
            "Replace this dry-run copy with Claude output before final delivery.",
        ],
    }

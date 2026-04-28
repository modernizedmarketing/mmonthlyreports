# tests/test_generate_insights_dry.py
import pytest
from unittest.mock import patch, MagicMock
from tools.generate_insights import (
    build_prompt,
    generate_insights,
    generate_insights_with_provider,
    generate_openai_insights,
    InsightProviderError,
)

SAMPLE_KPIS = {
    "google": {"revenue": 10000, "cost": 4000, "sales": 50, "leads": 200, "clicks": 1000,
               "impressions": 50000, "roas": 2.5, "cps": 80.0, "l2s_pct": 25.0, "cvr_pct": 5.0, "ctr_pct": 2.0, "aov": 200.0},
    "meta":   {"revenue": 5000,  "cost": 3000, "sales": 25, "leads": 100, "clicks": 500,
               "impressions": 25000, "roas": 1.67, "cps": 120.0, "l2s_pct": 25.0, "cvr_pct": 5.0, "ctr_pct": 2.0, "aov": 200.0},
    "bing":   {"revenue": 1200,  "cost": 600, "sales": 6, "leads": 40, "clicks": 250,
               "impressions": 12000, "roas": 2.0, "cps": 100.0, "l2s_pct": 15.0, "cvr_pct": 2.4, "ctr_pct": 2.08, "aov": 200.0},
    "google_funnels": {"TOF": {"cost": 1000, "revenue": 2000, "sales": 10, "leads": 50, "clicks": 250, "impressions": 10000, "roas": 2.0, "cps": 100.0, "l2s_pct": 20.0, "cvr_pct": 4.0}},
    "meta_funnels": {"MOF": {"cost": 3000, "revenue": 5000, "sales": 25, "leads": 100, "clicks": 500, "impressions": 25000, "roas": 1.67, "cps": 120.0, "l2s_pct": 25.0, "cvr_pct": 5.0}},
    "bing_funnels": {"BOF": {"cost": 600, "revenue": 1200, "sales": 6, "leads": 40, "clicks": 250, "impressions": 12000, "roas": 2.0, "cps": 100.0, "l2s_pct": 15.0, "cvr_pct": 2.4}},
    "google_funnel_cards": {"TOF": {"source": "TOF Search", "cost": 1000, "revenue": 2000, "sales": 10, "roas": 2.0}},
    "meta_funnel_cards": {"MOF": {"source": "MOF Retargeting", "cost": 3000, "revenue": 5000, "sales": 25, "roas": 1.67}},
    "bing_funnel_cards": {"BOF": {"source": "BOF Bing", "cost": 600, "revenue": 1200, "sales": 6, "roas": 2.0}},
    "google_top_ads": [{"source": "Branded Search", "funnel": "MOF", "cost": 1000, "revenue": 3000, "sales": 15, "roas": 3.0}],
    "meta_top_ads": [],
    "bing_top_ads": [],
    "total_funnel_distribution": {"TOF": {"cost": 1000, "cost_pct": 21.74, "revenue": 2000, "revenue_pct": 24.39}},
    "totals": {"cost": 7000, "revenue": 15000, "sales": 75, "roas": 2.14},
}

def test_build_prompt_contains_client_name():
    prompt = build_prompt("Funded Profit", "March", 2026, "February", 2026, SAMPLE_KPIS, {})
    assert "Funded Profit" in prompt
    assert "March" in prompt
    assert "February" in prompt
    assert "google_tof_narrative" in prompt
    assert "Currency for all money values" in prompt

def test_generate_insights_returns_dict(monkeypatch):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"slide3_general_insights": "test", "slide3_budget_roas": "test", "slide3_strategy": "test", "google_top_performer": "test", "google_main_drop": "test", "google_next_steps": "test", "meta_top_performer": "test", "meta_main_drop": "test", "meta_next_steps": "test", "performance_manager_narrative": "test", "action_items": ["a", "b"]}')]

    with patch("tools.generate_insights.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        result = generate_insights("Funded Profit", "March", 2026, "February", 2026, SAMPLE_KPIS, {})

    assert isinstance(result, dict)
    assert "slide3_general_insights" in result
    assert "action_items" in result


def test_generate_insights_with_provider_auto_requires_ai_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(InsightProviderError, match="requires ANTHROPIC_API_KEY or OPENAI_API_KEY"):
        generate_insights_with_provider(
            "auto",
            client="Funded Profit",
            month="March",
            year=2026,
            prev_month="February",
            prev_year=2026,
            kpis=SAMPLE_KPIS,
            user_overrides={},
            deterministic_factory=lambda: {"slide3_general_insights": "deterministic"},
        )


def test_generate_insights_with_provider_auto_uses_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "tools.generate_insights.generate_insights",
        lambda **_kwargs: {"slide3_general_insights": "anthropic"},
    )

    result, provider = generate_insights_with_provider(
        "auto",
        client="Funded Profit",
        month="March",
        year=2026,
        prev_month="February",
        prev_year=2026,
        kpis=SAMPLE_KPIS,
        user_overrides={},
    )

    assert provider == "anthropic"
    assert result["slide3_general_insights"] == "anthropic"


def test_generate_insights_with_provider_auto_uses_openai_when_anthropic_missing(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "tools.generate_insights.generate_openai_insights",
        lambda **_kwargs: {"slide3_general_insights": "openai"},
    )

    result, provider = generate_insights_with_provider(
        "auto",
        client="Funded Profit",
        month="March",
        year=2026,
        prev_month="February",
        prev_year=2026,
        kpis=SAMPLE_KPIS,
        user_overrides={},
    )

    assert provider == "openai"
    assert result["slide3_general_insights"] == "openai"


def test_generate_openai_insights_returns_dict(monkeypatch):
    mock_response = MagicMock()
    mock_response.output_text = '{"slide3_general_insights": "test", "slide3_budget_roas": "test", "slide3_strategy": "test", "google_top_performer": "test", "google_main_drop": "test", "google_next_steps": "test", "meta_top_performer": "test", "meta_main_drop": "test", "meta_next_steps": "test", "performance_manager_narrative": "test", "action_items": ["a", "b", "c", "d", "e"]}'

    with patch("tools.generate_insights.OpenAI") as mock_cls:
        mock_cls.return_value.responses.create.return_value = mock_response
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        result = generate_openai_insights("Funded Profit", "March", 2026, "February", 2026, SAMPLE_KPIS, {})

    assert isinstance(result, dict)
    assert result["action_items"][0] == "a"

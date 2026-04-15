# tests/test_generate_insights_dry.py
import pytest
from unittest.mock import patch, MagicMock
from tools.generate_insights import build_prompt, generate_insights

SAMPLE_KPIS = {
    "google": {"revenue": 10000, "cost": 4000, "sales": 50, "leads": 200, "clicks": 1000,
               "impressions": 50000, "roas": 2.5, "cps": 80.0, "l2s_pct": 25.0, "cvr_pct": 5.0, "ctr_pct": 2.0, "aov": 200.0},
    "meta":   {"revenue": 5000,  "cost": 3000, "sales": 25, "leads": 100, "clicks": 500,
               "impressions": 25000, "roas": 1.67, "cps": 120.0, "l2s_pct": 25.0, "cvr_pct": 5.0, "ctr_pct": 2.0, "aov": 200.0},
    "google_funnels": {"TOF": {"cost": 1000, "revenue": 2000, "sales": 10, "leads": 50, "roas": 2.0, "cps": 100.0, "l2s_pct": 20.0, "cvr_pct": 4.0}},
    "meta_funnels": {"MOF": {"cost": 3000, "revenue": 5000, "sales": 25, "leads": 100, "roas": 1.67, "cps": 120.0, "l2s_pct": 25.0, "cvr_pct": 5.0}},
    "google_top_ads": [{"source": "Branded Search", "funnel": "MOF", "cost": 1000, "revenue": 3000, "sales": 15, "roas": 3.0}],
    "meta_top_ads": [],
    "totals": {"cost": 7000, "revenue": 15000, "sales": 75, "roas": 2.14},
}

def test_build_prompt_contains_client_name():
    prompt = build_prompt("Funded Profit", "March", 2026, "February", SAMPLE_KPIS, {})
    assert "Funded Profit" in prompt
    assert "March" in prompt
    assert "February" in prompt

def test_generate_insights_returns_dict(monkeypatch):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"slide3_general_insights": "test", "slide3_budget_roas": "test", "slide3_strategy": "test", "google_top_performer": "test", "google_main_drop": "test", "google_next_steps": "test", "meta_top_performer": "test", "meta_main_drop": "test", "meta_next_steps": "test", "performance_manager_narrative": "test", "action_items": ["a", "b"]}')]

    with patch("tools.generate_insights.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        result = generate_insights("Funded Profit", "March", 2026, "February", SAMPLE_KPIS, {})

    assert isinstance(result, dict)
    assert "slide3_general_insights" in result
    assert "action_items" in result

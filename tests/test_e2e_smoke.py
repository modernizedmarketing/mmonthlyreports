# tests/test_e2e_smoke.py
"""Smoke test: run full pipeline on real March 2026 data (no API calls, no Drive)."""
import pandas as pd
import pytest
from pathlib import Path
from tools.validate_data import load_sheet, validate_or_raise
from tools.calculate_kpis import build_full_kpi_report

# The xlsx file is in the project root (two levels up from this worktree's tests/ dir)
XLSX_PATH = Path(__file__).parent.parent.parent.parent / "Monthly Data - March 2026.xlsx"
CLIENT = "Funded Profit"


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Excel file not present")
def test_funded_profit_checkpoints():
    campaigns = load_sheet(XLSX_PATH, "Campaigns", CLIENT)
    result = validate_or_raise(campaigns)
    assert result["checkpoint_1_passed"] is True


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Excel file not present")
def test_funded_profit_kpis():
    campaigns = load_sheet(XLSX_PATH, "Campaigns", CLIENT)
    ads = load_sheet(XLSX_PATH, "Ads", CLIENT)
    kpis = build_full_kpi_report(campaigns, ads)
    assert kpis["totals"]["cost"] > 0
    assert kpis["totals"]["roas"] > 0
    assert "google" in kpis
    assert "meta" in kpis
    print(f"\nFunded Profit March 2026: ROAS={kpis['totals']['roas']} | Cost=${kpis['totals']['cost']:,.2f} | Revenue=${kpis['totals']['revenue']:,.2f}")

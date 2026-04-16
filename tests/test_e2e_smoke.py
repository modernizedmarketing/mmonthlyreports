# tests/test_e2e_smoke.py
"""Smoke test: run pipeline on real March 2026 data (no API calls, no Drive)."""
import pytest
from pathlib import Path
from tools.validate_data import load_sheet, validate_or_raise
from tools.calculate_kpis import build_full_kpi_report
from tools.fill_pptx import build_replacements, fill_pptx
from tools.run_monthly_report import build_fake_insights, extract_placeholders

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "Funded Profit" / "2026-03"
XLSX_PATH = DATA_DIR / "Monthly Report March 2026.xlsx"
TEMPLATE_PATH = DATA_DIR / "previous_report.pptx"
OUTPUT_PATH = PROJECT_ROOT / "output" / "Funded Profit_March_2026_Report.pptx"
CLIENT = "Funded Profit"
MONTH = "March"
YEAR = 2026
PREV_MONTH = "February"
NEXT_MONTH = "April"


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Excel file not present")
def test_funded_profit_real_data_checkpoints():
    campaigns = load_sheet(XLSX_PATH, "Campaigns", CLIENT)
    result = validate_or_raise(campaigns)
    assert result["checkpoint_1_passed"] is True
    assert result["checkpoint_2_passed"] is True
    assert result["checkpoint_3_passed"] is True
    assert result["checkpoint_4_passed"] is True


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Excel file not present")
def test_funded_profit_real_data_kpis():
    campaigns = load_sheet(XLSX_PATH, "Campaigns", CLIENT)
    ads = load_sheet(XLSX_PATH, "Ads", CLIENT)
    kpis = build_full_kpi_report(campaigns, ads)
    assert kpis["totals"]["cost"] > 0
    assert kpis["totals"]["roas"] > 0
    assert "google" in kpis
    assert "meta" in kpis
    print(f"\nFunded Profit March 2026: ROAS={kpis['totals']['roas']} | Cost=${kpis['totals']['cost']:,.2f} | Revenue=${kpis['totals']['revenue']:,.2f}")


@pytest.mark.skipif(not XLSX_PATH.exists(), reason="Excel file not present")
@pytest.mark.skipif(not TEMPLATE_PATH.exists(), reason="PPTX template not present")
def test_funded_profit_real_data_pptx_dry_run():
    campaigns = load_sheet(XLSX_PATH, "Campaigns", CLIENT)
    ads = load_sheet(XLSX_PATH, "Ads", CLIENT)
    validate_or_raise(campaigns)
    kpis = build_full_kpi_report(campaigns, ads)
    overrides = {
        "company_revenue": 0,
        "ad_revenue": 0,
        "ad_cost": 0,
    }
    insights = build_fake_insights(kpis, CLIENT, MONTH, YEAR, NEXT_MONTH)
    replacements = build_replacements(
        CLIENT,
        MONTH,
        YEAR,
        PREV_MONTH,
        NEXT_MONTH,
        kpis,
        insights,
        overrides,
    )

    output_path = fill_pptx(TEMPLATE_PATH, OUTPUT_PATH, replacements)

    assert output_path.exists()
    remaining = extract_placeholders(output_path)
    # Current real template has no placeholders yet; once tagged, this catches missed replacements.
    assert remaining == set()

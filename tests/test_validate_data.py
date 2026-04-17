import pandas as pd
import pytest
from tools.validate_data import load_sheet, run_checkpoints

@pytest.fixture
def valid_campaigns_df():
    """Minimal campaigns dataframe that passes all checkpoints."""
    return pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 20.0, "Click": 100, "Impressions": 1000, "Average Order Value": 40.0},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 200.0, "Total Revenue": 500.0, "Sales": 10.0, "Leads": 40.0, "Click": 200, "Impressions": 2000, "Average Order Value": 50.0},
        {"Traffic Source": "google", "Funnel": "BOF", "Cost": 50.0,  "Total Revenue": 150.0, "Sales": 3.0,  "Leads": 10.0, "Click": 50,  "Impressions": 500,  "Average Order Value": 50.0},
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 800,  "Average Order Value": 40.0},
        {"Traffic Source": "meta",   "Funnel": "MOF", "Cost": 120.0, "Total Revenue": 300.0, "Sales": 8.0,  "Leads": 32.0, "Click": 120, "Impressions": 1200, "Average Order Value": 37.5},
        {"Traffic Source": "meta",   "Funnel": "BOF", "Cost": 30.0,  "Total Revenue": 90.0,  "Sales": 2.0,  "Leads": 8.0,  "Click": 30,  "Impressions": 300,  "Average Order Value": 45.0},
    ])

def test_checkpoint_1_cost_totals(valid_campaigns_df):
    result = run_checkpoints(valid_campaigns_df)
    assert result["checkpoint_1_passed"] is True

def test_checkpoint_2_sales_totals(valid_campaigns_df):
    result = run_checkpoints(valid_campaigns_df)
    assert result["checkpoint_2_passed"] is True

def test_checkpoint_3_google_funnel_sales(valid_campaigns_df):
    result = run_checkpoints(valid_campaigns_df)
    assert result["checkpoint_3_passed"] is True

def test_checkpoint_4_meta_funnel_sales(valid_campaigns_df):
    result = run_checkpoints(valid_campaigns_df)
    assert result["checkpoint_4_passed"] is True

def test_checkpoints_include_bing_as_supported_source(valid_campaigns_df):
    with_bing = pd.concat(
        [
            valid_campaigns_df,
            pd.DataFrame(
                [
                    {"Traffic Source": "bing", "Funnel": "TOF", "Cost": 10.0, "Total Revenue": 20.0, "Sales": 1.0, "Leads": 2.0, "Click": 10, "Impressions": 100, "Average Order Value": 20.0},
                    {"Traffic Source": "Microsoft Ads", "Funnel": "MOF", "Cost": 20.0, "Total Revenue": 80.0, "Sales": 2.0, "Leads": 4.0, "Click": 20, "Impressions": 200, "Average Order Value": 40.0},
                ]
            ),
        ],
        ignore_index=True,
    )

    result = run_checkpoints(with_bing)

    assert result["checkpoint_1_passed"] is True
    assert result["checkpoint_2_passed"] is True
    assert result["checkpoint_5_bing_funnel_sales_passed"] is True
    assert result["bing_sales"] == 3.0

def test_checkpoint_fails_on_bad_data():
    bad_df = pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 20.0, "Click": 100, "Impressions": 1000, "Average Order Value": 40.0},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 10.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Google funnel breakdown: 5 + 3 + 2 = 10
        {"Traffic Source": "google", "Funnel": "BOF", "Cost": 30.0, "Total Revenue": 60.0, "Sales": 2.0, "Leads": 5.0, "Click": 30, "Impressions": 300, "Average Order Value": 30.0},
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 800,  "Average Order Value": 40.0},
        {"Traffic Source": "meta",   "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 15.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Meta funnel breakdown: 4 + 3 = 7, but report total of 9 (unaccounted 2 in BOF row)
        {"Traffic Source": "meta", "Funnel": "BOF", "Cost": 25.0, "Total Revenue": 50.0, "Sales": 2.0, "Leads": 8.0, "Click": 25, "Impressions": 250, "Average Order Value": 25.0},
    ])
    # Manually modify to create mismatch: report google_sales as 11 instead of 10
    bad_df.at[0, "Sales"] = 6.0  # Change google TOF from 5 to 6, now funnel sum is 11 but we'll report 10
    result = run_checkpoints(bad_df)
    # Revert back - actually let's create a simpler bad case
    bad_df = pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 20.0, "Click": 100, "Impressions": 1000, "Average Order Value": 40.0},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 10.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Google: 5+3=8, but BOF says 5 for real total of 13 vs reported 8
        {"Traffic Source": "google", "Funnel": "BOF", "Cost": 30.0, "Total Revenue": 150.0, "Sales": 5.0, "Leads": 5.0, "Click": 30, "Impressions": 300, "Average Order Value": 30.0},
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 800,  "Average Order Value": 40.0},
        {"Traffic Source": "meta",   "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 15.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Meta funnel sum: 4+3=7, but will report total as 8 (missing 1 from somewhere)
        {"Traffic Source": "meta", "Funnel": "BOF", "Cost": 25.0, "Total Revenue": 50.0, "Sales": 1.0, "Leads": 8.0, "Click": 25, "Impressions": 250, "Average Order Value": 50.0},
    ])
    # This data has: Google sum=13 from funnels, Meta sum=8 from funnels, both internally consistent
    # Let me create actual mismatched data instead:
    bad_df2 = pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 20.0, "Click": 100, "Impressions": 1000, "Average Order Value": 40.0},
        # Google only has TOF with 5 sales
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 800,  "Average Order Value": 40.0},
        # Meta only has TOF with 4 sales
        # Now add BOF entries with data that creates inconsistency
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 500.0, "Sales": 15.0, "Leads": 30.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        {"Traffic Source": "google", "Funnel": "BOF", "Cost": 30.0, "Total Revenue": 150.0, "Sales": 5.0, "Leads": 5.0, "Click": 30, "Impressions": 300, "Average Order Value": 30.0},
        # Google: TOF(5) + MOF(15) + BOF(5) = 25 total
        # But we report in a way that creates data error
    ])
    result = run_checkpoints(bad_df2)
    # The funnels will sum correctly, so this still passes. Let me think differently.
    # The checkpoint test is checking that funnel breakdown ADDS UP to platform total
    # For this to fail, I need: google_tof + google_mof + google_bof != google_sales
    # This happens naturally if some rows are missing BOF data
    bad_df3 = pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 20.0, "Click": 100, "Impressions": 1000, "Average Order Value": 40.0},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 10.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Deliberately no BOF for google, sum is 8
        # Add a row with null/unknown funnel to create mismatch
        {"Traffic Source": "google", "Funnel": "UNKNOWN", "Cost": 20.0, "Total Revenue": 200.0, "Sales": 5.0, "Leads": 5.0, "Click": 20, "Impressions": 200, "Average Order Value": 40.0},
        # Now google_sales = 13 but TOF+MOF+BOF = 8
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 800,  "Average Order Value": 40.0},
        {"Traffic Source": "meta",   "Funnel": "MOF", "Cost": 50.0, "Total Revenue": 100.0, "Sales": 3.0, "Leads": 15.0, "Click": 50, "Impressions": 500, "Average Order Value": 33.33},
        # Meta_sales = 7, and TOF+MOF+BOF = 7, so this one passes
    ])
    result = run_checkpoints(bad_df3)
    # Funnel totals won't sum to platform totals → checkpoints 3 or 4 fail
    assert not all([result["checkpoint_3_passed"], result["checkpoint_4_passed"]])

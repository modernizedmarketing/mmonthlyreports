# tests/test_calculate_kpis.py
import pandas as pd
import pytest
from tools.calculate_kpis import (
    build_full_kpi_report,
    calculate_funnel_kpis,
    calculate_funnel_top_ads,
    calculate_platform_kpis,
    calculate_top_ads,
)

@pytest.fixture
def sample_campaigns():
    return pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "TOF", "Cost": 100.0, "Total Revenue": 250.0, "Sales": 5.0,  "Leads": 20.0, "Click": 100, "Impressions": 10000},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 200.0, "Total Revenue": 600.0, "Sales": 12.0, "Leads": 40.0, "Click": 200, "Impressions": 20000},
        {"Traffic Source": "google", "Funnel": "BOF", "Cost": 50.0,  "Total Revenue": 150.0, "Sales": 3.0,  "Leads": 10.0, "Click": 50,  "Impressions": 5000},
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 8000},
        {"Traffic Source": "meta",   "Funnel": "MOF", "Cost": 120.0, "Total Revenue": 300.0, "Sales": 8.0,  "Leads": 32.0, "Click": 120, "Impressions": 12000},
        {"Traffic Source": "meta",   "Funnel": "BOF", "Cost": 30.0,  "Total Revenue": 90.0,  "Sales": 2.0,  "Leads": 8.0,  "Click": 30,  "Impressions": 3000},
    ])

@pytest.fixture
def sample_ads():
    return pd.DataFrame([
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 150.0, "Total Revenue": 500.0, "Sales": 10.0, "Leads": 30.0, "Click": 150, "Impressions": 15000, "Source": "Ad_A - Google MOF"},
        {"Traffic Source": "google", "Funnel": "MOF", "Cost": 50.0,  "Total Revenue": 100.0, "Sales": 2.0,  "Leads": 8.0,  "Click": 50,  "Impressions": 5000,  "Source": "Ad_B - Google MOF"},
        {"Traffic Source": "meta",   "Funnel": "TOF", "Cost": 80.0,  "Total Revenue": 160.0, "Sales": 4.0,  "Leads": 16.0, "Click": 80,  "Impressions": 8000,  "Source": "Ad_C - Meta TOF"},
    ])

def test_google_roas(sample_campaigns):
    kpis = calculate_platform_kpis(sample_campaigns, "google")
    assert abs(kpis["roas"] - (250+600+150) / (100+200+50)) < 0.01

def test_google_cps(sample_campaigns):
    kpis = calculate_platform_kpis(sample_campaigns, "google")
    assert abs(kpis["cps"] - (100+200+50) / (5+12+3)) < 0.01

def test_google_l2s(sample_campaigns):
    kpis = calculate_platform_kpis(sample_campaigns, "google")
    expected = (5+12+3) / (20+40+10) * 100
    assert abs(kpis["l2s_pct"] - expected) < 0.01

def test_funnel_breakdown(sample_campaigns):
    funnels = calculate_funnel_kpis(sample_campaigns, "google")
    assert set(funnels.keys()) == {"TOF", "MOF", "BOF"}
    assert abs(funnels["MOF"]["roas"] - 600/200) < 0.01

def test_top_ads_sorted_by_total_revenue(sample_ads):
    top = calculate_top_ads(sample_ads, "google", n=2)
    assert top[0]["source"] == "Ad_A - Google MOF"
    assert len(top) == 2


def test_funnel_top_ads_selects_highest_revenue_ad_by_stage(sample_ads):
    top = calculate_funnel_top_ads(sample_ads, "google")

    assert top["MOF"]["source"] == "Ad_A - Google MOF"
    assert top["MOF"]["revenue"] == 500
    assert top["TOF"] == {}
    assert top["BOF"] == {}


def test_funnel_top_ads_ignores_zero_revenue_rows():
    ads = pd.DataFrame(
        [
            {"Traffic Source": "google", "Funnel": "BOF", "Cost": 50, "Total Revenue": 0, "Sales": 0, "Leads": 1, "Click": 10, "Impressions": 100, "Source": "Zero Rev"},
            {"Traffic Source": "google", "Funnel": "TOF", "Cost": 20, "Total Revenue": 100, "Sales": 1, "Leads": 2, "Click": 5, "Impressions": 50, "Source": "Positive Rev"},
        ]
    )

    top = calculate_funnel_top_ads(ads, "google")

    assert top["BOF"] == {}
    assert top["TOF"]["source"] == "Positive Rev"


def test_full_kpi_report_keeps_aggregate_funnels_and_ad_card_rows(sample_campaigns, sample_ads):
    report = build_full_kpi_report(sample_campaigns, sample_ads)

    assert report["google_funnels"]["MOF"]["revenue"] == 600
    assert report["google_funnel_cards"]["MOF"]["revenue"] == 500
    assert report["meta_funnels"]["TOF"]["revenue"] == 160
    assert report["meta_funnel_cards"]["TOF"]["source"] == "Ad_C - Meta TOF"

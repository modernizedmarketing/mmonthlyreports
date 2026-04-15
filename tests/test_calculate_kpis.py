# tests/test_calculate_kpis.py
import pandas as pd
import pytest
from tools.calculate_kpis import calculate_platform_kpis, calculate_funnel_kpis, calculate_top_ads

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

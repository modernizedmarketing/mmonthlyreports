# tools/calculate_kpis.py
# NOTE: All revenue values are read from the "Total Revenue" column, not "Revenue" or "Recurring Revenue".
import pandas as pd

def _safe_divide(num: float, den: float, default: float = 0.0) -> float:
    return num / den if den != 0 else default

def calculate_platform_kpis(df: pd.DataFrame, platform: str) -> dict:
    """Calculate aggregate KPIs for a platform (google or meta)."""
    p = df[df["Traffic Source"].str.lower() == platform.lower()]
    cost     = p["Cost"].sum()
    revenue  = p["Total Revenue"].sum()  # Always use Total Revenue
    sales    = p["Sales"].sum()
    leads    = p["Leads"].sum()
    clicks   = p["Click"].sum()
    impr     = p["Impressions"].sum()
    return {
        "cost":     round(cost, 2),
        "revenue":  round(revenue, 2),
        "sales":    round(sales, 0),
        "leads":    round(leads, 0),
        "clicks":   round(clicks, 0),
        "impressions": round(impr, 0),
        "roas":     round(_safe_divide(revenue, cost), 2),
        "cps":      round(_safe_divide(cost, sales), 2),
        "cpl":      round(_safe_divide(cost, leads), 2),
        "l2s_pct":  round(_safe_divide(sales, leads) * 100, 2),
        "cvr_pct":  round(_safe_divide(sales, clicks) * 100, 2),
        "ctr_pct":  round(_safe_divide(clicks, impr) * 100, 2),
        "aov":      round(_safe_divide(revenue, sales), 2),
    }

def calculate_funnel_kpis(df: pd.DataFrame, platform: str) -> dict:
    """Calculate KPIs per funnel (TOF/MOF/BOF) for a platform."""
    p = df[df["Traffic Source"].str.lower() == platform.lower()]
    result = {}
    for funnel in ["TOF", "MOF", "BOF"]:
        f = p[p["Funnel"].str.upper() == funnel]
        if f.empty:
            result[funnel] = {}
            continue
        cost    = f["Cost"].sum()
        revenue = f["Total Revenue"].sum()  # Always use Total Revenue
        sales   = f["Sales"].sum()
        leads   = f["Leads"].sum()
        clicks  = f["Click"].sum()
        impr    = f["Impressions"].sum()
        result[funnel] = {
            "cost":     round(cost, 2),
            "revenue":  round(revenue, 2),
            "sales":    round(sales, 0),
            "leads":    round(leads, 0),
            "clicks":   round(clicks, 0),
            "impressions": round(impr, 0),
            "roas":     round(_safe_divide(revenue, cost), 2),
            "cps":      round(_safe_divide(cost, sales), 2),
            "l2s_pct":  round(_safe_divide(sales, leads) * 100, 2),
            "cvr_pct":  round(_safe_divide(sales, clicks) * 100, 2),
        }
    return result

def calculate_top_ads(df: pd.DataFrame, platform: str, n: int = 10) -> list:
    """Return top N ads by Total Revenue for a platform."""
    p = df[df["Traffic Source"].str.lower() == platform.lower()].copy()
    p = p.sort_values("Total Revenue", ascending=False).head(n)  # Sort by Total Revenue
    results = []
    for _, row in p.iterrows():
        cost    = float(row.get("Cost", 0))
        revenue = float(row.get("Total Revenue", 0))  # Always use Total Revenue
        sales   = float(row.get("Sales", 0))
        results.append({
            "source":  str(row.get("Source", row.get("Source Link", "Unknown"))),
            "funnel":  str(row.get("Funnel", "")),
            "cost":    round(cost, 2),
            "revenue": round(revenue, 2),
            "sales":   round(sales, 0),
            "roas":    round(_safe_divide(revenue, cost), 2),
        })
    return results

def build_full_kpi_report(campaigns_df: pd.DataFrame, ads_df: pd.DataFrame) -> dict:
    """
    Build the complete KPI dict consumed by generate_insights and fill_pptx.
    All revenue figures derive from the "Total Revenue" column.
    """
    google = calculate_platform_kpis(campaigns_df, "google")
    meta   = calculate_platform_kpis(campaigns_df, "meta")

    total_cost    = round(google["cost"] + meta["cost"], 2)
    total_revenue = round(google["revenue"] + meta["revenue"], 2)
    total_sales   = round(google["sales"] + meta["sales"], 0)

    return {
        "google":       google,
        "meta":         meta,
        "google_funnels": calculate_funnel_kpis(campaigns_df, "google"),
        "meta_funnels":   calculate_funnel_kpis(campaigns_df, "meta"),
        "google_top_ads": calculate_top_ads(ads_df, "google"),
        "meta_top_ads":   calculate_top_ads(ads_df, "meta"),
        "totals": {
            "cost":    total_cost,
            "revenue": total_revenue,
            "sales":   total_sales,
            "roas":    round(total_revenue / total_cost if total_cost else 0, 2),
        },
    }

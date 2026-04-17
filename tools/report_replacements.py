"""Build formatted placeholder values for monthly Google Slides reports."""
from __future__ import annotations

from typing import Any, Callable


REQUIRED_TEMPLATE_TOKENS = {
    "{{CLIENT}}",
    "{{REPORT_MONTH}}",
    "{{SLIDE4_AD_REVENUE}}",
    "{{SLIDE4_AD_COST}}",
    "{{SLIDE4_ROAS}}",
    "{{SLIDE4_CPS}}",
    "{{SLIDE4_L2S}}",
    "{{SLIDE4_CVR}}",
    "{{SLIDE4_AOV}}",
    "{{COMPANY_REVENUE}}",
    "{{PCT_REV_FROM_ADS}}",
    "{{GOOGLE_REVENUE}}",
    "{{GOOGLE_COST}}",
    "{{GOOGLE_SALES}}",
    "{{GOOGLE_ROAS}}",
    "{{GOOGLE_CPS}}",
    "{{GOOGLE_CTR}}",
    "{{GOOGLE_CVR}}",
    "{{GOOGLE_L2S}}",
    "{{META_REVENUE}}",
    "{{META_COST}}",
    "{{META_SALES}}",
    "{{META_ROAS}}",
    "{{META_CPS}}",
    "{{META_CTR}}",
    "{{META_CVR}}",
    "{{META_L2S}}",
    "{{SLIDE3_GENERAL_INSIGHTS}}",
    "{{SLIDE3_BUDGET_ROAS}}",
    "{{SLIDE3_STRATEGY}}",
    "{{GOOGLE_TOP_PERFORMER}}",
    "{{GOOGLE_NEXT_STEPS}}",
    "{{META_TOP_PERFORMER}}",
    "{{META_NEXT_STEPS}}",
    "{{PM_NARRATIVE}}",
    "{{ACTION_ITEM_1}}",
    "{{ACTION_ITEM_2}}",
    "{{ACTION_ITEM_3}}",
    "{{ACTION_ITEM_4}}",
    "{{ACTION_ITEM_5}}",
}


def fmt_pct(value: float | int | None) -> str:
    return f"{float(value or 0):.2f}%"


def fmt_pct_whole(value: float | int | None) -> str:
    return f"{float(value or 0):.0f}%"


def fmt_pct_card(value: float | int | None) -> str:
    numeric = float(value or 0)
    return f"{numeric:.0f}%" if abs(numeric) >= 10 else f"{numeric:.1f}%"


def fmt_usd(value: float | int | None) -> str:
    return f"${float(value or 0):,.2f}"


def fmt_usd_whole(value: float | int | None) -> str:
    return f"${float(value or 0):,.0f}"


def fmt_usd_compact(value: float | int | None) -> str:
    numeric = float(value or 0)
    if abs(numeric) >= 1000:
        return f"${numeric / 1000:,.0f}K"
    return fmt_usd_whole(numeric)


def fmt_int(value: float | int | None) -> str:
    return f"{int(float(value or 0)):,}"


def fmt_roas(value: float | int | None) -> str:
    return f"{float(value or 0):.2f}"


def fmt_roas_card(value: float | int | None) -> str:
    numeric = float(value or 0)
    if abs(numeric) >= 10:
        return f"{numeric:.0f}"
    return f"{numeric:.1f}"


def _safe_value(data: dict[str, Any], key: str, formatter: Callable[[Any], str]) -> str:
    value = data.get(key)
    if value is None:
        return ""
    return formatter(value)


def _funnel_value(funnels: dict[str, Any], stage: str, key: str, formatter: Callable[[Any], str]) -> str:
    stage_data = funnels.get(stage)
    if not stage_data or key not in stage_data or stage_data.get(key) is None:
        return "N/A"
    return formatter(stage_data.get(key))


def _platform_replacements(prefix: str, data: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, str]:
    previous = previous or {}
    token = prefix.upper()
    return {
        f"{{{{{token}_ROAS}}}}": fmt_roas(data.get("roas", 0)) if data else "",
        f"{{{{{token}_CPS}}}}": fmt_usd(data.get("cps", 0)) if data else "",
        f"{{{{{token}_L2S}}}}": fmt_pct(data.get("l2s_pct", 0)) if data else "",
        f"{{{{{token}_CVR}}}}": fmt_pct(data.get("cvr_pct", 0)) if data else "",
        f"{{{{{token}_CTR}}}}": fmt_pct(data.get("ctr_pct", 0)) if data else "",
        f"{{{{{token}_REVENUE}}}}": fmt_usd(data.get("revenue", 0)) if data else "",
        f"{{{{{token}_COST}}}}": fmt_usd(data.get("cost", 0)) if data else "",
        f"{{{{{token}_SALES}}}}": fmt_int(data.get("sales", 0)) if data else "",
        f"{{{{{token}_CLICKS}}}}": fmt_int(data.get("clicks", 0)) if data else "",
        f"{{{{{token}_IMPRESSIONS}}}}": fmt_int(data.get("impressions", 0)) if data else "",
        f"{{{{{token}_LEADS}}}}": fmt_int(data.get("leads", 0)) if data else "",
        f"{{{{{token}_ROAS_PREV}}}}": _safe_value(previous, "roas", fmt_roas),
        f"{{{{{token}_CPS_PREV}}}}": _safe_value(previous, "cps", fmt_usd),
        f"{{{{{token}_L2S_PREV}}}}": _safe_value(previous, "l2s_pct", fmt_pct),
        f"{{{{{token}_CVR_PREV}}}}": _safe_value(previous, "cvr_pct", fmt_pct),
        f"{{{{{token}_CTR_PREV}}}}": _safe_value(previous, "ctr_pct", fmt_pct),
    }


def _funnel_replacements(prefix: str, funnels: dict[str, Any]) -> dict[str, str]:
    token = prefix.upper()
    replacements: dict[str, str] = {}
    for stage in ("TOF", "MOF", "BOF"):
        replacements.update(
            {
                f"{{{{{token}_{stage}_REVENUE}}}}": _funnel_value(funnels, stage, "revenue", fmt_usd),
                f"{{{{{token}_{stage}_COST}}}}": _funnel_value(funnels, stage, "cost", fmt_usd),
                f"{{{{{token}_{stage}_ROAS}}}}": _funnel_value(funnels, stage, "roas", fmt_roas),
                f"{{{{{token}_{stage}_SALES}}}}": _funnel_value(funnels, stage, "sales", fmt_int),
                f"{{{{{token}_{stage}_CPS}}}}": _funnel_value(funnels, stage, "cps", fmt_usd),
                f"{{{{{token}_{stage}_CR}}}}": _funnel_value(funnels, stage, "cvr_pct", fmt_pct),
            }
        )
    return replacements


def _funnel_card_replacements(prefix: str, funnels: dict[str, Any]) -> dict[str, str]:
    token = prefix.upper()
    replacements: dict[str, str] = {}
    for stage in ("TOF", "MOF", "BOF"):
        replacements.update(
            {
                f"{{{{{token}_{stage}_REVENUE}}}}": _funnel_value(funnels, stage, "revenue", fmt_usd_compact),
                f"{{{{{token}_{stage}_COST}}}}": _funnel_value(funnels, stage, "cost", fmt_usd_whole),
                f"{{{{{token}_{stage}_ROAS}}}}": _funnel_value(funnels, stage, "roas", fmt_roas_card),
                f"{{{{{token}_{stage}_SALES}}}}": _funnel_value(funnels, stage, "sales", fmt_int),
                f"{{{{{token}_{stage}_CPS}}}}": _funnel_value(funnels, stage, "cps", fmt_usd_whole),
                f"{{{{{token}_{stage}_CR}}}}": _funnel_value(funnels, stage, "cvr_pct", fmt_pct_card),
            }
        )
    return replacements


def build_audit_replacements(
    client: str,
    month: str,
    year: int,
    prev_month: str,
    next_month: str,
) -> dict[str, str]:
    """Build a complete sample replacement map for template-only audits."""
    platform_sample = {
        "revenue": 1000,
        "cost": 500,
        "sales": 10,
        "leads": 50,
        "clicks": 250,
        "impressions": 10000,
        "roas": 2,
        "cps": 50,
        "l2s_pct": 20,
        "cvr_pct": 4,
        "ctr_pct": 2.5,
    }
    funnel_sample = {
        stage: {
            "revenue": 1000,
            "cost": 500,
            "sales": 10,
            "cps": 50,
            "roas": 2,
            "cvr_pct": 4,
        }
        for stage in ("TOF", "MOF", "BOF")
    }
    kpis = {
        "google": dict(platform_sample),
        "meta": dict(platform_sample),
        "bing": dict(platform_sample),
        "google_funnels": dict(funnel_sample),
        "meta_funnels": dict(funnel_sample),
        "bing_funnels": dict(funnel_sample),
        "totals": {
            "revenue": 3000,
            "cost": 1500,
            "sales": 30,
            "roas": 2,
            "cps": 50,
            "l2s_pct": 20,
            "cvr_pct": 4,
            "aov": 100,
        },
    }
    insights = {
        "slide3_general_insights": "Sample general insights.",
        "slide3_budget_roas": "Sample budget and ROAS note.",
        "slide3_strategy": "Sample strategy note.",
        "google_top_performer": "Sample Google top performer.",
        "google_main_drop": "Sample Google main drop.",
        "google_next_steps": "Sample Google next steps.",
        "meta_top_performer": "Sample Meta top performer.",
        "meta_main_drop": "Sample Meta main drop.",
        "meta_next_steps": "Sample Meta next steps.",
        "performance_manager_narrative": "Sample performance manager narrative.",
        "action_items": [
            "Sample action item 1.",
            "Sample action item 2.",
            "Sample action item 3.",
            "Sample action item 4.",
            "Sample action item 5.",
        ],
    }
    overrides = {
        "company_revenue": 5000,
        "ad_revenue": 3000,
        "ad_cost": 1500,
        "prev_company_revenue": 4000,
        "prev_ad_revenue": 2400,
        "prev_ad_cost": 1200,
    }
    return build_replacements(
        client,
        month,
        year,
        prev_month,
        next_month,
        kpis,
        insights,
        overrides,
        prev_kpis=kpis,
    )


def build_replacements(
    client: str,
    month: str,
    year: int,
    prev_month: str,
    next_month: str,
    kpis: dict,
    insights: dict,
    user_overrides: dict,
    prev_kpis: dict | None = None,
) -> dict[str, str]:
    """Build the full placeholder-to-value map for Google Slides reports."""
    totals = kpis["totals"]
    prev_totals = prev_kpis.get("totals", {}) if prev_kpis else {}
    ad_revenue = user_overrides.get("ad_revenue") or totals["revenue"]
    ad_cost = user_overrides.get("ad_cost") or totals["cost"]
    company_revenue = user_overrides.get("company_revenue", 0)

    slide4_roas = fmt_roas(ad_revenue / ad_cost) if ad_cost else fmt_roas(totals.get("roas", 0))
    slide4_cps = fmt_usd(ad_cost / totals["sales"]) if totals.get("sales") else "$0.00"
    pct_rev = fmt_pct_whole(ad_revenue / company_revenue * 100) if company_revenue else "0%"

    p_company_revenue = user_overrides.get("prev_company_revenue", 0)
    p_ad_revenue = user_overrides.get("prev_ad_revenue") or prev_totals.get("revenue", 0)
    p_ad_cost = user_overrides.get("prev_ad_cost") or prev_totals.get("cost", 0)
    p_sales = prev_totals.get("sales", 0)
    p_slide4_roas = fmt_roas(p_ad_revenue / p_ad_cost) if prev_kpis and p_ad_cost else ""
    p_slide4_cps = fmt_usd(p_ad_cost / p_sales) if prev_kpis and p_sales else ""
    p_pct_rev = fmt_pct_whole(p_ad_revenue / p_company_revenue * 100) if prev_kpis and p_company_revenue else ""
    action_items = insights.get("action_items", [])

    replacements = {
        "{{MONTH}}": month,
        "{{YEAR}}": str(year),
        "{{REPORT_MONTH}}": f"{month} {year}",
        "{{MONTH_YEAR}}": f"{month} {year}",
        "{{CLIENT}}": client,
        "{{PREV_MONTH}}": prev_month,
        "{{NEXT_MONTH}}": next_month,
        "{{SLIDE4_AD_REVENUE}}": fmt_usd(ad_revenue),
        "{{SLIDE4_AD_COST}}": fmt_usd(ad_cost),
        "{{SLIDE4_ROAS}}": slide4_roas,
        "{{SLIDE4_CPS}}": slide4_cps,
        "{{SLIDE4_L2S}}": fmt_pct(totals.get("l2s_pct", 0)),
        "{{SLIDE4_CVR}}": fmt_pct(totals.get("cvr_pct", 0)),
        "{{SLIDE4_AOV}}": fmt_usd(totals.get("aov", 0)),
        "{{COMPANY_REVENUE}}": fmt_usd(company_revenue),
        "{{PCT_REV_FROM_ADS}}": pct_rev,
        "{{SLIDE4_AD_REVENUE_PREV}}": fmt_usd(p_ad_revenue) if prev_kpis else "",
        "{{SLIDE4_AD_COST_PREV}}": fmt_usd(p_ad_cost) if prev_kpis else "",
        "{{SLIDE4_ROAS_PREV}}": p_slide4_roas,
        "{{SLIDE4_CPS_PREV}}": p_slide4_cps,
        "{{SLIDE4_L2S_PREV}}": fmt_pct(prev_totals.get("l2s_pct", 0)) if prev_kpis else "",
        "{{SLIDE4_CVR_PREV}}": fmt_pct(prev_totals.get("cvr_pct", 0)) if prev_kpis else "",
        "{{SLIDE4_AOV_PREV}}": fmt_usd(prev_totals.get("aov", 0)) if prev_kpis else "",
        "{{COMPANY_REVENUE_PREV}}": fmt_usd(p_company_revenue) if prev_kpis else "",
        "{{PCT_REV_FROM_ADS_PREV}}": p_pct_rev,
        "{{SLIDE3_GENERAL_INSIGHTS}}": insights.get("slide3_general_insights", ""),
        "{{SLIDE3_BUDGET_ROAS}}": insights.get("slide3_budget_roas", ""),
        "{{SLIDE3_STRATEGY}}": insights.get("slide3_strategy", ""),
        "{{GOOGLE_TOP_PERFORMER}}": insights.get("google_top_performer", ""),
        "{{GOOGLE_MAIN_DROP}}": insights.get("google_main_drop", ""),
        "{{GOOGLE_NEXT_STEPS}}": insights.get("google_next_steps", ""),
        "{{META_TOP_PERFORMER}}": insights.get("meta_top_performer", ""),
        "{{META_MAIN_DROP}}": insights.get("meta_main_drop", ""),
        "{{META_NEXT_STEPS}}": insights.get("meta_next_steps", ""),
        "{{PM_NARRATIVE}}": insights.get("performance_manager_narrative", ""),
    }

    for index in range(5):
        replacements[f"{{{{ACTION_ITEM_{index + 1}}}}}"] = action_items[index] if len(action_items) > index else ""

    replacements.update(_platform_replacements("google", kpis["google"], prev_kpis.get("google", {}) if prev_kpis else None))
    replacements.update(_platform_replacements("meta", kpis["meta"], prev_kpis.get("meta", {}) if prev_kpis else None))
    replacements.update(_platform_replacements("bing", kpis.get("bing", {}), prev_kpis.get("bing", {}) if prev_kpis else None))
    replacements.update(_funnel_card_replacements("google", kpis.get("google_funnel_cards", kpis.get("google_funnels", {}))))
    replacements.update(_funnel_card_replacements("meta", kpis.get("meta_funnel_cards", kpis.get("meta_funnels", {}))))
    replacements.update(_funnel_card_replacements("bing", kpis.get("bing_funnel_cards", kpis.get("bing_funnels", {}))))

    return {key: "" if value is None else str(value) for key, value in replacements.items()}

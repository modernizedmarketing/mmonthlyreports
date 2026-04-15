"""
Edits a PPTX template by replacing {{placeholder}} tokens with real values.
All font properties (name, size, bold, color) are preserved on replacement.
"""
import shutil
from pathlib import Path
from typing import Optional, Dict, Union
from pptx import Presentation
from pptx.dml.color import RGBColor


def _safe_rgb(run) -> Optional[RGBColor]:
    """Read font color without crashing on SchemeColor."""
    try:
        return run.font.color.rgb
    except Exception:
        return None


def _replace_in_run(run, replacements: dict):
    """Replace placeholder tokens in a single run, preserving font properties."""
    text = run.text
    for placeholder, value in replacements.items():
        if placeholder in text:
            text = text.replace(placeholder, str(value))
    if text != run.text:
        # Capture existing formatting
        font_name = run.font.name
        font_size = run.font.size
        bold      = run.font.bold
        rgb       = _safe_rgb(run)
        run.text = text
        # Restore formatting
        if font_name:       run.font.name = font_name
        if font_size:       run.font.size = font_size
        if bold is not None: run.font.bold = bold
        if rgb:             run.font.color.rgb = rgb


def _replace_in_shape(shape, replacements: dict):
    """Recursively replace placeholders in all text frames and tables."""
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                _replace_in_run(run, replacements)
    if shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        _replace_in_run(run, replacements)
    # Handle grouped shapes
    if hasattr(shape, "shapes"):
        for child in shape.shapes:
            _replace_in_shape(child, replacements)


def build_replacements(
    client: str,
    month: str,
    year: int,
    prev_month: str,
    next_month: str,
    kpis: dict,
    insights: dict,
    user_overrides: dict,
) -> dict:
    """Build the full placeholder → value dict for all slides."""
    g  = kpis["google"]
    m  = kpis["meta"]
    t  = kpis["totals"]
    gf = kpis["google_funnels"]
    mf = kpis["meta_funnels"]
    ov = user_overrides

    def fmt_pct(v): return f"{v:.2f}%"
    def fmt_usd(v): return f"${v:,.2f}"
    def fmt_int(v): return f"{int(v):,}"

    ad_revenue = ov.get("ad_revenue", t["revenue"])
    ad_cost    = ov.get("ad_cost", t["cost"])
    slide4_roas = f"{ad_revenue / ad_cost:.2f}" if ad_cost else str(t["roas"])

    return {
        # Slide 1 — Title
        "{{MONTH}}":      month,
        "{{YEAR}}":       str(year),
        "{{CLIENT}}":     client,
        "{{PREV_MONTH}}": prev_month,
        "{{NEXT_MONTH}}": next_month,
        # Slide 4 — Total Ads (user override values)
        "{{SLIDE4_AD_REVENUE}}": fmt_usd(ad_revenue),
        "{{SLIDE4_AD_COST}}":    fmt_usd(ad_cost),
        "{{SLIDE4_ROAS}}":       slide4_roas,
        "{{SLIDE4_CPS}}":        fmt_usd(ad_cost / t["sales"] if t["sales"] else 0),
        "{{COMPANY_REVENUE}}":   fmt_usd(ov.get("company_revenue", 0)),
        # Slide 6 — Google KPIs
        "{{GOOGLE_ROAS}}":        str(g["roas"]),
        "{{GOOGLE_CPS}}":         fmt_usd(g["cps"]),
        "{{GOOGLE_L2S}}":         fmt_pct(g["l2s_pct"]),
        "{{GOOGLE_CVR}}":         fmt_pct(g["cvr_pct"]),
        "{{GOOGLE_CTR}}":         fmt_pct(g["ctr_pct"]),
        "{{GOOGLE_REVENUE}}":     fmt_usd(g["revenue"]),
        "{{GOOGLE_COST}}":        fmt_usd(g["cost"]),
        "{{GOOGLE_SALES}}":       fmt_int(g["sales"]),
        # Slide 8 — Google volume
        "{{GOOGLE_CLICKS}}":      fmt_int(g["clicks"]),
        "{{GOOGLE_IMPRESSIONS}}": fmt_int(g["impressions"]),
        "{{GOOGLE_LEADS}}":       fmt_int(g["leads"]),
        # Google Funnel
        "{{GOOGLE_TOF_REVENUE}}": fmt_usd(gf.get("TOF", {}).get("revenue", 0)),
        "{{GOOGLE_TOF_COST}}":    fmt_usd(gf.get("TOF", {}).get("cost", 0)),
        "{{GOOGLE_TOF_ROAS}}":    str(gf.get("TOF", {}).get("roas", 0)),
        "{{GOOGLE_TOF_SALES}}":   fmt_int(gf.get("TOF", {}).get("sales", 0)),
        "{{GOOGLE_MOF_REVENUE}}": fmt_usd(gf.get("MOF", {}).get("revenue", 0)),
        "{{GOOGLE_MOF_COST}}":    fmt_usd(gf.get("MOF", {}).get("cost", 0)),
        "{{GOOGLE_MOF_ROAS}}":    str(gf.get("MOF", {}).get("roas", 0)),
        "{{GOOGLE_MOF_SALES}}":   fmt_int(gf.get("MOF", {}).get("sales", 0)),
        "{{GOOGLE_BOF_REVENUE}}": fmt_usd(gf.get("BOF", {}).get("revenue", 0)),
        "{{GOOGLE_BOF_COST}}":    fmt_usd(gf.get("BOF", {}).get("cost", 0)),
        "{{GOOGLE_BOF_ROAS}}":    str(gf.get("BOF", {}).get("roas", 0)),
        "{{GOOGLE_BOF_SALES}}":   fmt_int(gf.get("BOF", {}).get("sales", 0)),
        # Meta KPIs
        "{{META_ROAS}}":    str(m["roas"]),
        "{{META_CPS}}":     fmt_usd(m["cps"]),
        "{{META_L2S}}":     fmt_pct(m["l2s_pct"]),
        "{{META_CVR}}":     fmt_pct(m["cvr_pct"]),
        "{{META_CTR}}":     fmt_pct(m["ctr_pct"]),
        "{{META_REVENUE}}": fmt_usd(m["revenue"]),
        "{{META_COST}}":    fmt_usd(m["cost"]),
        "{{META_SALES}}":   fmt_int(m["sales"]),
        # Meta Funnel
        "{{META_TOF_REVENUE}}": fmt_usd(mf.get("TOF", {}).get("revenue", 0)),
        "{{META_TOF_ROAS}}":    str(mf.get("TOF", {}).get("roas", 0)),
        "{{META_MOF_REVENUE}}": fmt_usd(mf.get("MOF", {}).get("revenue", 0)),
        "{{META_MOF_ROAS}}":    str(mf.get("MOF", {}).get("roas", 0)),
        "{{META_BOF_REVENUE}}": fmt_usd(mf.get("BOF", {}).get("revenue", 0)),
        "{{META_BOF_ROAS}}":    str(mf.get("BOF", {}).get("roas", 0)),
        # Slide 3 — AI Insights
        "{{SLIDE3_GENERAL_INSIGHTS}}": insights.get("slide3_general_insights", ""),
        "{{SLIDE3_BUDGET_ROAS}}":      insights.get("slide3_budget_roas", ""),
        "{{SLIDE3_STRATEGY}}":         insights.get("slide3_strategy", ""),
        "{{GOOGLE_TOP_PERFORMER}}":    insights.get("google_top_performer", ""),
        "{{GOOGLE_MAIN_DROP}}":        insights.get("google_main_drop", ""),
        "{{GOOGLE_NEXT_STEPS}}":       insights.get("google_next_steps", ""),
        "{{META_TOP_PERFORMER}}":      insights.get("meta_top_performer", ""),
        "{{META_MAIN_DROP}}":          insights.get("meta_main_drop", ""),
        "{{META_NEXT_STEPS}}":         insights.get("meta_next_steps", ""),
        "{{PM_NARRATIVE}}":            insights.get("performance_manager_narrative", ""),
        "{{ACTION_ITEM_1}}": insights.get("action_items", [""] * 5)[0] if len(insights.get("action_items", [])) > 0 else "",
        "{{ACTION_ITEM_2}}": insights.get("action_items", [""] * 5)[1] if len(insights.get("action_items", [])) > 1 else "",
        "{{ACTION_ITEM_3}}": insights.get("action_items", [""] * 5)[2] if len(insights.get("action_items", [])) > 2 else "",
        "{{ACTION_ITEM_4}}": insights.get("action_items", [""] * 5)[3] if len(insights.get("action_items", [])) > 3 else "",
        "{{ACTION_ITEM_5}}": insights.get("action_items", [""] * 5)[4] if len(insights.get("action_items", [])) > 4 else "",
    }


def fill_pptx(
    template_path: Union[str, Path],
    output_path: Union[str, Path],
    replacements: Dict,
) -> Path:
    """
    Copy template PPTX to output_path, then replace all {{placeholder}} tokens.
    Returns the output path.
    """
    template_path = Path(template_path)
    output_path   = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(template_path, output_path)
    prs = Presentation(output_path)

    for slide in prs.slides:
        for shape in slide.shapes:
            _replace_in_shape(shape, replacements)

    prs.save(output_path)
    return output_path

# tools/generate_insights.py
import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)

def _dumps(obj, **kwargs):
    return json.dumps(obj, cls=_NumpyEncoder, **kwargs)

def build_prompt(
    client: str,
    month: str,
    year: int,
    prev_month: str,
    kpis: dict,
    user_overrides: dict,
    media_buyer_notes: str = "",
    special_requests: str = "",
) -> str:
    return f"""You are a senior performance marketing analyst for prop firms.
Company: {client}
Report Month: {month} {year}
Previous Month: {prev_month} {year}

=== CURRENT MONTH KPIs ===
Google: Revenue ${kpis['google']['revenue']:,.2f} | Cost ${kpis['google']['cost']:,.2f} | ROAS {kpis['google']['roas']} | Sales {int(kpis['google']['sales'])} | CPS ${kpis['google']['cps']:,.2f} | L2S {kpis['google']['l2s_pct']}% | CVR {kpis['google']['cvr_pct']}% | CTR {kpis['google']['ctr_pct']}%
Meta:   Revenue ${kpis['meta']['revenue']:,.2f} | Cost ${kpis['meta']['cost']:,.2f} | ROAS {kpis['meta']['roas']} | Sales {int(kpis['meta']['sales'])} | CPS ${kpis['meta']['cps']:,.2f} | L2S {kpis['meta']['l2s_pct']}% | CVR {kpis['meta']['cvr_pct']}% | CTR {kpis['meta']['ctr_pct']}%
Total:  Revenue ${kpis['totals']['revenue']:,.2f} | Cost ${kpis['totals']['cost']:,.2f} | ROAS {kpis['totals']['roas']}

=== FUNNEL BREAKDOWN ===
Google TOF: {_dumps(kpis['google_funnels'].get('TOF', {}))}
Google MOF: {_dumps(kpis['google_funnels'].get('MOF', {}))}
Google BOF: {_dumps(kpis['google_funnels'].get('BOF', {}))}
Meta TOF: {_dumps(kpis['meta_funnels'].get('TOF', {}))}
Meta MOF: {_dumps(kpis['meta_funnels'].get('MOF', {}))}
Meta BOF: {_dumps(kpis['meta_funnels'].get('BOF', {}))}

=== TOP ADS (Google) ===
{_dumps(kpis['google_top_ads'][:5], indent=2)}

=== TOP ADS (Meta) ===
{_dumps(kpis['meta_top_ads'][:5], indent=2)}

=== USER OVERRIDES (Slide 4 only) ===
Company Revenue: ${user_overrides.get('company_revenue', 0):,.2f}
Ad Revenue: ${user_overrides.get('ad_revenue', 0):,.2f}
Ad Cost: ${user_overrides.get('ad_cost', 0):,.2f}

=== MEDIA BUYER NOTES ===
{media_buyer_notes or 'None provided.'}

=== SPECIAL REQUESTS ===
{special_requests or 'None.'}

Generate the following JSON. Every insight MUST follow DATA → INSIGHT → ACTION framework. Use exact numbers. Never be generic.

{{
  "slide3_general_insights": "...",
  "slide3_budget_roas": "...",
  "slide3_strategy": "...",
  "google_top_performer": "...",
  "google_main_drop": "...",
  "google_next_steps": "...",
  "meta_top_performer": "...",
  "meta_main_drop": "...",
  "meta_next_steps": "...",
  "performance_manager_narrative": "...",
  "action_items": ["...", "...", "...", "...", "..."]
}}"""


def generate_insights(
    client: str,
    month: str,
    year: int,
    prev_month: str,
    kpis: dict,
    user_overrides: dict,
    media_buyer_notes: str = "",
    special_requests: str = "",
) -> dict:
    """
    Call Claude API and return parsed JSON dict of slide narratives.
    Uses prompt caching on the system prompt for cost efficiency.
    """
    client_sdk = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = build_prompt(
        client, month, year, prev_month,
        kpis, user_overrides, media_buyer_notes, special_requests
    )

    response = client_sdk.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": "You are a senior performance marketing analyst specialized in paid media for prop firms. Always respond with valid JSON only. No markdown code blocks, no preamble.",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

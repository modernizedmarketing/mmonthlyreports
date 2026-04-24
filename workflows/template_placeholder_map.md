# Template Placeholder Map - One Funded Monthly Report

Template inspected:
`https://docs.google.com/presentation/d/1sDL6pLcf-KrFDFu7F-vVLvdGr8azo55RGxEGEs1sCiU/edit`

Use this file as the exact slide-by-slide checklist for turning the current branded deck into an automation-ready Google Slides template.

## Global Rules

- Replace the existing visible example value with the placeholder.
- Keep labels like `Revenue`, `Sales`, `ROAS`, `CPS`, `CR`, `Purchases`, `Leads`, etc.
- Put placeholders only where a generated value should appear.
- Do not add new tokens that are not listed here unless we also update `tools/report_replacements.py`.
- Slides marked **Manual/static for now** should not receive placeholders yet, otherwise `--audit-only` may fail.
- For paragraphs, replace the whole paragraph body with the placeholder, not individual numbers inside the paragraph.

## Slide 1 - Cover

Replace:

- `One Funded` under the `Client` label -> `{{CLIENT}}`
- `March 2026` under the `Period` label -> `{{REPORT_MONTH}}`

Leave:

- `Monthly Marketing Report`
- `Human Crafted, AI Amplified`

## Slide 2 - Overview

Manual/static for now.

No placeholders needed unless section names change month-to-month.

## Slide 3 - Monthly Insights

Replace the three main body text boxes:

- Large `General Insights` body text beginning with `March closed strong...` -> `{{SLIDE3_GENERAL_INSIGHTS}}`
- `Budget / ROAS / Revenue` body text beginning with `In March, we had a goal...` -> `{{SLIDE3_BUDGET_ROAS}}`
- `Overall Strategy` body text beginning with `Two main changes were made...` -> `{{SLIDE3_STRATEGY}}`

Keep the section headers:

- `General Insights`
- `Budget / ROAS / Revenue`
- `Overall Strategy`
- `Monthly Insights`

## Slide 4 - High Level Results / Total Ads Results

Current month values:

- Main top revenue value `$41,402.51` -> `{{SLIDE4_AD_REVENUE}}`
- Main top ad spend value `$24,184.63` -> `{{SLIDE4_AD_COST}}`
- Main `ROAS` value `1.71` -> `{{SLIDE4_ROAS}}`
- Main `Cost Per Sale` value `$45.12` -> `{{SLIDE4_CPS}}`
- Main `Lead To Sale` value `15.44%` -> `{{SLIDE4_L2S}}`
- Main `Conv. Rate` value `1.68%` -> `{{SLIDE4_CVR}}`
- Main `AOV` value `$77.24` -> `{{SLIDE4_AOV}}`
- `Company Revenue` value `$93,051` -> `{{COMPANY_REVENUE}}`
- `% Of Revenue From Ads` value `44%` -> `{{PCT_REV_FROM_ADS}}`

Previous month comparison values:

- `$68,210` -> `{{COMPANY_REVENUE_PREV}}`
- `45%` -> `{{PCT_REV_FROM_ADS_PREV}}`
- `$30,752.14` -> `{{SLIDE4_AD_REVENUE_PREV}}`
- `$15,587.33` -> `{{SLIDE4_AD_COST_PREV}}`
- `1.97` -> `{{SLIDE4_ROAS_PREV}}`
- `$36.50` -> `{{SLIDE4_CPS_PREV}}`
- `16.92%` -> `{{SLIDE4_L2S_PREV}}`
- `2.30%` -> `{{SLIDE4_CVR_PREV}}`
- `$72.02` -> `{{SLIDE4_AOV_PREV}}`

Keep benchmark labels/values static for now.

## Slide 5 - Google Ads Services

Manual/static for now.

No placeholders needed.

## Slide 6 - Google Results

Current month values:

- Black/current `ROAS` value `2.39` -> `{{GOOGLE_ROAS}}`
- Black/current `Cost Per Sale` value `$38.88` -> `{{GOOGLE_CPS}}`
- Black/current `Lead To Sale` value `16.30%` -> `{{GOOGLE_L2S}}`
- Black/current `Conv. Rate` value `3.22%` -> `{{GOOGLE_CVR}}`
- Black/current `CTR` value `0.84%` -> `{{GOOGLE_CTR}}`

Previous month values:

- Red/previous `ROAS` value `2.07` -> `{{GOOGLE_ROAS_PREV}}`
- Red/previous `Cost Per Sale` value `$31.01` -> `{{GOOGLE_CPS_PREV}}`
- Red/previous `Lead To Sale` value `19.28%` -> `{{GOOGLE_L2S_PREV}}`
- Red/previous `Conv. Rate` value `3.74%` -> `{{GOOGLE_CVR_PREV}}`
- Red/previous `CTR` value `0.88%` -> `{{GOOGLE_CTR_PREV}}`

Keep benchmark labels/values static for now.

## Slide 7 - Google Scope Of Work

Manual/static for now.

The current automation does not yet generate scope-of-work counts or media buyer text for this slide.

Do not add placeholders yet.

## Slide 8 - Google Ads Funnel Narrative

Top KPI row:

- `Purchases` value `428` -> `{{GOOGLE_SALES}}`
- `Leads` value `2,625` -> `{{GOOGLE_LEADS}}`
- `Clicks` value `13,275` -> `{{GOOGLE_CLICKS}}`
- `Impressions` value `1,571,728` -> `{{GOOGLE_IMPRESSIONS}}`
- `Leads to Sale Ratio` value `16.30%` -> `{{GOOGLE_L2S}}`
- `Conv. Rate` value `3.22%` -> `{{GOOGLE_CVR}}`

Funnel narrative text boxes:

- TOF paragraph beginning `1.3M Impressions | 6.1K Clicks...` -> `{{GOOGLE_TOF_NARRATIVE}}`
- MOF paragraph beginning `228.0K Impressions | 7.1K Clicks...` -> `{{GOOGLE_MOF_NARRATIVE}}`
- BOF paragraph beginning `3.6K Impressions | 61.0 Clicks...` -> `{{GOOGLE_BOF_NARRATIVE}}`

These are now code-supported. Final report runs should use the LLM provider for polished copy; audit/deterministic runs use metric-based fallback text so the template can still pass without API access.

## Slide 9 - Google Funnel Metric Cards

TOF card:

- Revenue `$1k` -> `{{GOOGLE_TOF_REVENUE}}`
- Sales `3` -> `{{GOOGLE_TOF_SALES}}`
- ROAS `19` -> `{{GOOGLE_TOF_ROAS}}`
- CPS `$18` -> `{{GOOGLE_TOF_CPS}}`
- CR `27%` -> `{{GOOGLE_TOF_CR}}`

MOF card:

- Revenue `$26K` -> `{{GOOGLE_MOF_REVENUE}}`
- Sales `304` -> `{{GOOGLE_MOF_SALES}}`
- ROAS `5.4` -> `{{GOOGLE_MOF_ROAS}}`
- CPS `$16` -> `{{GOOGLE_MOF_CPS}}`
- CR `6.4%` -> `{{GOOGLE_MOF_CR}}`

BOF card:

- This slide visually labels BOF, but extracted text only shows TOF/MOF values. If there is a hidden/blank BOF card, use:
- Revenue -> `{{GOOGLE_BOF_REVENUE}}`
- Sales -> `{{GOOGLE_BOF_SALES}}`
- ROAS -> `{{GOOGLE_BOF_ROAS}}`
- CPS -> `{{GOOGLE_BOF_CPS}}`
- CR -> `{{GOOGLE_BOF_CR}}`

## Slide 10 - Google Ads Results Monthly Comparison

Manual/static for now.

This is likely a chart slide. We should automate it later with linked Google Sheets charts.

## Slide 11 - Meta Ads Services

Manual/static for now.

No placeholders needed.

## Slide 12 - Meta Results

Current month values:

- Black/current `ROAS` value `0.36` -> `{{META_ROAS}}`
- Black/current `Cost Per Sale` value `$64.31` -> `{{META_CPS}}`
- Black/current `Lead To Sale` value `7.93%` -> `{{META_L2S}}`
- Black/current `Conv. Rate` value `0.22%` -> `{{META_CVR}}`
- Black/current `CTR` value `0.72%` -> `{{META_CTR}}`

Previous month values:

- Red/previous `ROAS` value `0.82` -> `{{META_ROAS_PREV}}`
- Red/previous `Cost Per Sale` value `$123.96` -> `{{META_CPS_PREV}}`
- Red/previous `Lead To Sale` value `6.11%` -> `{{META_L2S_PREV}}`
- Red/previous `Conv. Rate` value `0.37%` -> `{{META_CVR_PREV}}`
- Red/previous `CTR` value `0.70%` -> `{{META_CTR_PREV}}`

Keep benchmark labels/values static for now.

## Slide 13 - Meta Scope Of Work

Manual/static for now.

Do not add placeholders yet.

## Slide 14 - Meta Ads Funnel Narrative

Top KPI row:

- `Purchases` value `36` -> `{{META_SALES}}`
- `Leads` value `454` -> `{{META_LEADS}}`
- `Clicks` value `16,257` -> `{{META_CLICKS}}`
- `Impressions` value `2,272,273` -> `{{META_IMPRESSIONS}}`
- `Leads to Sale Ratio` value `7.93%` -> `{{META_L2S}}`
- `Conv. Rate` value `0.22%` -> `{{META_CVR}}`

Funnel narrative text boxes:

- TOF paragraph beginning `2.1M Impressions | 15.1K Clicks...` -> `{{META_TOF_NARRATIVE}}`
- MOF paragraph beginning `94.6K Impressions | 653.0 Clicks...` -> `{{META_MOF_NARRATIVE}}`
- BOF paragraph beginning `40.8K Impressions | 548.0 Clicks...` -> `{{META_BOF_NARRATIVE}}`

Do not add CTR, CPL, or CPC cards on this slide. The supported KPI cards here are Lead to Sale Ratio and Conv. Rate.

## Slide 15 - Meta TOF/MOF Funnel Metric Cards

TOF card:

- Revenue `$189` -> `{{META_TOF_REVENUE}}`
- Sales `3` -> `{{META_TOF_SALES}}`
- ROAS `2` -> `{{META_TOF_ROAS}}`
- CPS `$30` -> `{{META_TOF_CPS}}`
- CR `13%` -> `{{META_TOF_CR}}`

MOF card:

- Revenue `$390` -> `{{META_MOF_REVENUE}}`
- Sales `7` -> `{{META_MOF_SALES}}`
- ROAS `9` -> `{{META_MOF_ROAS}}`
- CPS `$6` -> `{{META_MOF_CPS}}`
- CR `3.4%` -> `{{META_MOF_CR}}`

## Slide 16 - Meta BOF Funnel Metric Card

BOF card:

- Revenue `$117` -> `{{META_BOF_REVENUE}}`
- Sales `5` -> `{{META_BOF_SALES}}`
- ROAS `2` -> `{{META_BOF_ROAS}}`
- CPS `$12` -> `{{META_BOF_CPS}}`
- CR `1.1%` -> `{{META_BOF_CR}}`

## Slide 17 - Meta Ads Results Monthly Comparison

Manual/static for now.

Automate later with linked Google Sheets charts.

## Slide 18 - Bing Ads Services

Manual/static for now.

No placeholders needed.

## Slide 19 - Bing Results

Current month values:

- Black/current `ROAS` value `0.92` -> `{{BING_ROAS}}`
- Black/current `Cost Per Sale` value `$42.82` -> `{{BING_CPS}}`
- Black/current `Lead To Sale` value `18.37%` -> `{{BING_L2S}}`
- Black/current `Conv. Rate` value `3.01%` -> `{{BING_CVR}}`
- Black/current `CTR` value `1.48%` -> `{{BING_CTR}}`

Previous month values:

- Red/previous `ROAS` value `1.74` -> `{{BING_ROAS_PREV}}`
- Red/previous `Cost Per Sale` value `$71.39` -> `{{BING_CPS_PREV}}`
- Red/previous `Lead To Sale` value `19.66%` -> `{{BING_L2S_PREV}}`
- Red/previous `Conv. Rate` value `2.92%` -> `{{BING_CVR_PREV}}`
- Red/previous `CTR` value `1.48%` -> `{{BING_CTR_PREV}}`

Keep benchmark labels/values static for now.

## Slide 20 - Bing Scope Of Work

Manual/static for now.

Do not add placeholders yet.

## Slide 21 - Bing Ads Funnel Narrative

Top KPI row:

- `Purchases` value `72` -> `{{BING_SALES}}`
- `Leads` value `392` -> `{{BING_LEADS}}`
- `Clicks` value `2,395` -> `{{BING_CLICKS}}`
- `Impressions` value `161,869` -> `{{BING_IMPRESSIONS}}`
- `Leads to Sale Ratio` value `18.37%` -> `{{BING_L2S}}`
- `Conv. Rate` value `3.01%` -> `{{BING_CVR}}`

Funnel narrative text boxes:

- TOF paragraph beginning `159.8K Impressions | 2.0K Clicks...` -> `{{BING_TOF_NARRATIVE}}`
- MOF paragraph beginning `1.3K Impressions | 428.0 Clicks...` -> `{{BING_MOF_NARRATIVE}}`

`{{BING_BOF_NARRATIVE}}` is code-supported for future use, but the current master deck only has TOF and MOF narrative boxes on this Bing slide.

## Slide 22 - Bing Funnel Metric Cards

TOF card:

- Revenue `$929` -> `{{BING_TOF_REVENUE}}`
- Sales `26` -> `{{BING_TOF_SALES}}`
- ROAS `0.5` -> `{{BING_TOF_ROAS}}`
- CPS `$74` -> `{{BING_TOF_CPS}}`
- CR `1.3%` -> `{{BING_TOF_CR}}`

MOF card:

- Revenue `$4.4K` -> `{{BING_MOF_REVENUE}}`
- Sales `46` -> `{{BING_MOF_SALES}}`
- ROAS `4` -> `{{BING_MOF_ROAS}}`
- CPS `$25` -> `{{BING_MOF_CPS}}`
- CR `11%` -> `{{BING_MOF_CR}}`

BOF card:

- Only add BOF placeholders if you keep a visible BOF card on this slide.
- Revenue -> `{{BING_BOF_REVENUE}}`
- Sales -> `{{BING_BOF_SALES}}`
- ROAS -> `{{BING_BOF_ROAS}}`
- CPS -> `{{BING_BOF_CPS}}`
- CR -> `{{BING_BOF_CR}}`

## Slide 23 - Bing Ads Results Monthly Comparison

Manual/static for now.

Automate later with linked Google Sheets charts.

## Slide 24 - Total Ads Performance

Manual/static for now unless it is the funnel distribution visual in the Full Services master deck.

For the Full Services funnel distribution slide, use:

- TOF ad spend value -> `{{TOTAL_TOF_COST}}`
- TOF ad spend share -> `{{TOTAL_TOF_COST_PCT}}`
- MOF ad spend value -> `{{TOTAL_MOF_COST}}`
- MOF ad spend share -> `{{TOTAL_MOF_COST_PCT}}`
- BOF ad spend value -> `{{TOTAL_BOF_COST}}`
- BOF ad spend share -> `{{TOTAL_BOF_COST_PCT}}`
- TOF ad revenue value -> `{{TOTAL_TOF_REVENUE}}`
- TOF ad revenue share -> `{{TOTAL_TOF_REVENUE_PCT}}`
- MOF ad revenue value -> `{{TOTAL_MOF_REVENUE}}`
- MOF ad revenue share -> `{{TOTAL_MOF_REVENUE_PCT}}`
- BOF ad revenue value -> `{{TOTAL_BOF_REVENUE}}`
- BOF ad revenue share -> `{{TOTAL_BOF_REVENUE_PCT}}`

Values come from Campaigns across Google, Meta, and Bing/Microsoft by funnel stage. Money uses compact report currency formatting (`$28K` or `€28K`) and percentages are whole numbers.

## Slide 25 - Total Ads Results Monthly Comparison

Manual/static for now.

Likely chart/image slide. Automate later with linked Google Sheets charts.

## Slide 26 - MT5 Engagement Campaigns

Manual/static for now.

No matching replacement tokens exist yet for engagement-only campaign data.

## Slide 27 - Top 10 Creatives META

Manual/static for now.

Creative screenshots/media should remain manually curated unless we later add asset automation.

## Slide 28 - March Creatives

Manual/static for now.

## Slide 29 - March Creatives

Manual/static for now.

## Slide 30 - Giveaway Landing

Manual/static for now.

This slide has landing-page-specific metrics. Do not add placeholders yet unless we create a landing-page data model.

## Slide 31 - Cheat Sheet Landing

Manual/static for now.

Do not add placeholders yet.

## Slide 32 - Trader Quiz Landing

Manual/static for now.

Do not add placeholders yet.

## Slide 33 - MT5 Data

Manual/static for now.

This can be automated later if MT5 data becomes a standard tab/range in the Google Sheet.

## Slide 34 - GEO Strategy

Manual/static for now.

This is strategy/list copy, not currently generated by the KPI pipeline.

## Slide 35 - March Insights / Action Items

Replace:

- Title `March Insights` -> `{{MONTH}} Insights`
- Whole body text box with the monthly summary and next steps -> `{{PM_NARRATIVE}}`

Alternative if you want separate action bullets:

- Keep the first summary paragraph manual or replace with `{{PM_NARRATIVE}}`
- Replace five separate next-step bullet lines with:
  - `{{ACTION_ITEM_1}}`
  - `{{ACTION_ITEM_2}}`
  - `{{ACTION_ITEM_3}}`
  - `{{ACTION_ITEM_4}}`
  - `{{ACTION_ITEM_5}}`

Do not put all five action item placeholders in one paragraph unless you want them generated as separate lines in the same text box.

## Slide 36 - ClickCease

Manual/static for now.

No ClickCease data model exists in the automation yet.

## Slide 37 - Social Moderation

Manual/static for now.

No moderation data model exists in the automation yet.

## Slide 38 - Blank

Manual/static for now.

Can be deleted from the template later if it is not needed.

## Audit Command

After adding the placeholders above, run:

```bash
python3 tools/run_google_slides_report.py \
  --spreadsheet "GOOGLE_SHEET_URL_OR_ID" \
  --template-presentation "https://docs.google.com/presentation/d/1sDL6pLcf-KrFDFu7F-vVLvdGr8azo55RGxEGEs1sCiU/edit" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --audit-only
```

Expected:

- `missing_values` should be empty.
- `unused_values` can contain extra tokens; that is okay.
- If `missing_values` contains tokens ending in `_NARRATIVE`, remove those from the deck or ask to add narrative-token support.

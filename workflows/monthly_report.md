# Monthly Marketing Report — Workflow SOP

## Objective
Generate the monthly PPTX marketing report for a single client using Hyros xlsx exports, then upload it to Google Drive.

## Required Inputs (ask user for these before starting)
- `client` — exact client name as it appears in the Client column (e.g. "Funded Profit")
- `month` — report month (e.g. "March")
- `year` — report year (e.g. 2026)
- `prev_month` — previous month name (e.g. "February")
- `next_month` — next month name (e.g. "April") — used for Action Items slide
- `company_revenue` — total company revenue (user-provided override, for Slide 4)
- `ad_revenue` — total ad revenue (user-provided override, for Slide 4)
- `ad_cost` — total ad spend (user-provided override, for Slide 4)
- `media_buyer_notes` — optional context from the media buyer
- `special_requests` — optional client-specific analysis requests

## Required Files (user drops these into data/[client]/[YYYY-MM]/ before running)
1. `Monthly Report [Month] [Year].xlsx` — Hyros export with 2 sheets:
   - Sheet "Campaigns" — all clients' campaign data; filter by Client column
   - Sheet "Ads" — all clients' ad data; filter by Client column
2. `previous_report.pptx` — Last month's finished PPTX (used as template)

## Steps

### Step 1: Load and validate data
```python tools/validate_data.py```
- Find the xlsx file in `data/[client]/[YYYY-MM]/` (glob for `Monthly Report*.xlsx`)
- Load Campaigns sheet: `load_sheet(path, "Campaigns", client)`
- Load Ads sheet: `load_sheet(path, "Ads", client)`
- Run `validate_or_raise(campaigns_df)` — raises ValueError if any of the 4 checkpoints fail
- If a checkpoint fails: STOP and report which totals don't match. Do not proceed.

### Step 2: Calculate KPIs
```python tools/calculate_kpis.py```
- Run `build_full_kpi_report(campaigns_df, ads_df)`
- Returns the full kpis dict with google, meta, funnels, top ads, totals
- All revenue values derive from the "Total Revenue" column

### Step 3: Generate AI insights
```python tools/generate_insights.py```
- Run `generate_insights(...)` with all data from Step 2 plus user overrides
- Returns JSON dict with all slide narratives
- If Claude API fails: retry once. If it fails again, ask user to check ANTHROPIC_API_KEY.

### Step 4: Fill PPTX template
```python tools/fill_pptx.py```
- Template: `data/[client]/[YYYY-MM]/previous_report.pptx`
- Output: `output/[client]_[Month]_[Year]_Report.pptx`
- Run `build_replacements(...)` then `fill_pptx(template, output, replacements)`
- CRITICAL: The template must have {{PLACEHOLDER}} tokens. If placeholders are missing, alert user — the template needs to be tagged first.

### Step 5: Upload to Google Drive
```python tools/upload_to_drive.py```
- Run `upload_to_drive(output_path)`
- Returns shareable URL — present this to the user

### Step 6: Confirm delivery
- Report the Google Drive URL to the user
- Confirm all 4 verification checkpoints passed
- Note any placeholders that were NOT replaced (search the output PPTX for remaining {{ tokens)

## Error Handling
- **Checkpoint failure**: Report exact numbers. Do not proceed. Ask user to fix source xlsx.
- **Missing xlsx**: Tell user exactly which file is missing and where to place it.
- **Claude API error**: Retry once. If fails again, ask user to check .env ANTHROPIC_API_KEY.
- **Drive upload error**: Save file locally to output/ and give user the local path.
- **Template has no placeholders**: Generate a placeholder-tagging checklist for the user to update their template PPTX.

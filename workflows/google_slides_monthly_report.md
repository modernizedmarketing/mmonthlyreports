# Google Slides Monthly Marketing Report — Workflow SOP

## Objective
Generate a branded monthly Google Slides report from the canonical Google Sheet, using Python for KPI validation/calculation and Google Slides API replacement for the final deck.

## Required Inputs
- `spreadsheet` — Google Sheet URL or ID containing Hyros report data.
- `template_presentation` — master Google Slides template URL or ID.
- `client` — exact Client column value.
- `month`, `year`, `prev_month`, `next_month`.
- Optional overrides: `company_revenue`, `ad_revenue`, `ad_cost`, `prev_company_revenue`, `prev_ad_revenue`, `prev_ad_cost`, media buyer notes, special requests.

## Required Google Sheet Tabs
- `Campaigns` — Hyros campaign rows. Custom tab names can be passed with `--campaigns-sheet`.
- `Ads` — Hyros ad rows. Custom tab names can be passed with `--ads-sheet`.
- `Manual Inputs` — optional row-based or key/value inputs for company revenue, ad revenue, ad cost, notes, and requests.
- `KPI Output` — written by the runner.
- `Run Log` — appended by the runner.

## Template Rules
- Use native Google Slides as the master template.
- Place `{{TOKEN}}` strings only in intentional text boxes or table cells.
- Never generate a template by globally replacing old numbers with tokens.
- Prefer complete-field tokens such as `{{GOOGLE_TOF_SALES}}`, `{{META_BOF_ROAS}}`, and full narrative tokens such as `{{GOOGLE_NEXT_STEPS}}`.
- Platform summary and total results use aggregate rows from the `Campaigns` tab.
- Funnel card placeholders such as `{{GOOGLE_TOF_REVENUE}}` use the highest-`Total Revenue` ad row for that platform/funnel from the `Ads` tab.
- Funnel card rows with zero `Total Revenue` are ignored; if no positive-revenue ad exists for that stage, the card shows `N/A`.
- `% Of Revenue From Ads` is rounded to a whole percent for client-facing consistency.
- Use `workflows/template_placeholder_map.md` as the source of truth for template creation.

## Dry-Run Audit
Run this before generating a client deck:

```bash
python3 tools/run_google_slides_report.py \
  --template-presentation "GOOGLE_SLIDES_TEMPLATE_URL_OR_ID" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --audit-only
```

The audit must show no `missing_values`. `unused_values` are okay; they mean the code can fill more tokens than this template currently uses.

## Generate a Deck
```bash
python3 tools/run_google_slides_report.py \
  --spreadsheet "GOOGLE_SHEET_URL_OR_ID" \
  --template-presentation "GOOGLE_SLIDES_TEMPLATE_URL_OR_ID" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --company-revenue 93051 \
  --prev-company-revenue 68210 \
  --output-title "One Funded March 2026 Report - Automated" \
  --thumbnail-audit
```

By default this uses fake/dry-run insights. Add `--use-claude` for final narrative generation after the template audit passes.

## One Funded Test Command
```bash
python3 tools/run_google_slides_report.py \
  --spreadsheet "https://docs.google.com/spreadsheets/d/1QVOZAlPiD86t6qt32R-uS0cseQ6eeYn_m5WKoXrQ9B4/edit" \
  --template-presentation "https://docs.google.com/presentation/d/1sDL6pLcf-KrFDFu7F-vVLvdGr8azo55RGxEGEs1sCiU/edit" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --campaigns-sheet "Campaigns OneFunded" \
  --ads-sheet "Ads OneFunded" \
  --company-revenue 93051 \
  --prev-company-revenue 68210 \
  --output-title "One Funded March 2026 Report - Dry Run" \
  --thumbnail-audit
```

This reads March as the current month and February as the previous month from the same spreadsheet, then fills both current and `_PREV` placeholders.

## Production Runner
Use the same CLI inside a Cloud Run job. Set `GOOGLE_SERVICE_ACCOUNT_FILE` to a service-account JSON path or mount credentials through the runtime. Share the Sheet, Slides template, and Drive output folder with that service account.

Cloud Scheduler or a manual Cloud Run trigger can run the job so report generation does not depend on a local Codex/Claude Code session.

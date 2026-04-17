# Agent Instructions

This project now focuses on one production workflow:

**Google Sheets -> Python KPI logic -> Google Slides**

The old local PPTX-editing path is retired. Do not reintroduce scripts that tag or edit PowerPoint files by replacing old visible numbers.

## Architecture

Use the WAT pattern:

- **Workflows** live in `workflows/` and explain what to run.
- **Tools** live in `tools/` and perform deterministic work.
- **Agents** coordinate the workflow, inspect failures, and call tools in order.

The main SOP is:

```text
workflows/google_slides_monthly_report.md
```

## Source Of Truth

- Hyros campaign/ad data lives in Google Sheets.
- Python calculates and validates KPIs.
- Google Slides is the branded presentation template and final editable report.
- Google Drive stores deliverables.
- Local files are only for development, tests, or temporary exports.

## Live Tools

Keep these as the core runtime:

- `tools/validate_data.py`
- `tools/calculate_kpis.py`
- `tools/generate_insights.py`
- `tools/report_insights.py`
- `tools/report_replacements.py`
- `tools/google_workspace.py`
- `tools/google_sheet_report_data.py`
- `tools/google_slides_report.py`
- `tools/run_google_slides_report.py`

## Template Rules

- The branded report template must be a native Google Slides deck.
- Put `{{TOKEN}}` placeholders only in intentional text boxes or table cells.
- Run `--audit-only` before generating a real deck.
- Never create placeholders by reverse-tagging old report numbers.
- Prefer full-field tokens like `{{GOOGLE_TOF_SALES}}` or full narrative boxes like `{{GOOGLE_NEXT_STEPS}}`.
- Use `workflows/template_placeholder_map.md` when building or reviewing a template.

## Credentials And Secrets

Secrets stay local and out of git:

- `.env`
- `.env.local`
- `credentials.json`
- `token.pickle`
- `token_workspace.pickle`
- service-account JSON files

Safe examples belong in `.env.example`.

## Normal Run

Audit first:

```bash
python3 tools/run_google_slides_report.py \
  --spreadsheet "GOOGLE_SHEET_URL_OR_ID" \
  --template-presentation "GOOGLE_SLIDES_TEMPLATE_URL_OR_ID" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --audit-only
```

Generate after the audit passes:

```bash
python3 tools/run_google_slides_report.py \
  --spreadsheet "GOOGLE_SHEET_URL_OR_ID" \
  --template-presentation "GOOGLE_SLIDES_TEMPLATE_URL_OR_ID" \
  --client "One Funded" \
  --month March --year 2026 \
  --prev-month February --next-month April \
  --company-revenue 93051 \
  --thumbnail-audit
```

Add `--use-claude` only when generating final narrative copy.

## Verification

Before calling a change done, run:

```bash
python3 -m pytest -q
python3 -m py_compile tools/*.py
python3 tools/run_google_slides_report.py --help
```

If a command uses paid APIs or creates client-visible reports, run a dry audit first and make the side effect explicit.

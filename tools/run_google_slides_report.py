#!/usr/bin/env python3
"""Generate a monthly report from Google Sheets into a copied Google Slides deck."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.calculate_kpis import build_full_kpi_report
from tools.generate_insights import generate_insights
from tools.google_sheet_report_data import (
    append_run_log,
    load_report_sheet,
    make_run_log_row,
    read_manual_inputs,
    write_kpi_output,
)
from tools.google_slides_report import (
    audit_placeholders,
    build_slides_replacements,
    copy_presentation,
    export_presentation,
    get_slide_thumbnail_urls,
    read_placeholders,
    refresh_linked_sheets_charts,
    replace_placeholders,
)
from tools.google_workspace import build_workspace_services, extract_file_id
from tools.report_insights import assert_insights_shape, build_fake_insights
from tools.report_replacements import build_audit_replacements
from tools.validate_data import validate_or_raise

PDF_MIME = "application/pdf"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Google Sheets -> Google Slides report pipeline.")
    parser.add_argument("--spreadsheet", default="", help="Google Sheet URL or ID")
    parser.add_argument("--template-presentation", required=True, help="Google Slides template URL or ID")
    parser.add_argument("--client", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--prev-month", required=True)
    parser.add_argument("--next-month", required=True)
    parser.add_argument("--campaigns-sheet", default="Campaigns")
    parser.add_argument("--ads-sheet", default="Ads")
    parser.add_argument("--manual-inputs-sheet", default="Manual Inputs")
    parser.add_argument("--kpi-output-sheet", default="KPI Output")
    parser.add_argument("--run-log-sheet", default="Run Log")
    parser.add_argument("--output-folder-id", default=os.environ.get("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", ""))
    parser.add_argument("--output-title", default="")
    parser.add_argument("--company-revenue", type=float, default=None)
    parser.add_argument("--ad-revenue", type=float, default=None)
    parser.add_argument("--ad-cost", type=float, default=None)
    parser.add_argument("--prev-company-revenue", type=float, default=None)
    parser.add_argument("--prev-ad-revenue", type=float, default=None)
    parser.add_argument("--prev-ad-cost", type=float, default=None)
    parser.add_argument("--media-buyer-notes", default="")
    parser.add_argument("--special-requests", default="")
    parser.add_argument("--use-claude", action="store_true")
    parser.add_argument("--audit-only", action="store_true", help="Audit template tokens without copying or editing.")
    parser.add_argument("--skip-run-log", action="store_true")
    parser.add_argument("--skip-kpi-output", action="store_true")
    parser.add_argument("--skip-chart-refresh", action="store_true")
    parser.add_argument("--thumbnail-audit", action="store_true", help="Print thumbnail URLs for quick visual checks.")
    parser.add_argument("--export-pdf-path", default="")
    parser.add_argument("--export-pptx-path", default="")
    return parser.parse_args()


def _manual_or_arg(
    manual: dict,
    args: argparse.Namespace,
    key: str,
    default: float = 0.0,
    manual_key: str | None = None,
) -> float:
    cli_value = getattr(args, key.replace("-", "_"), None)
    if cli_value is not None:
        return cli_value
    lookup = manual_key or key
    value = manual.get(lookup.replace("-", "_"), manual.get(lookup, default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    args = parse_args()
    template_id = extract_file_id(args.template_presentation)
    services = build_workspace_services()

    if args.audit_only:
        replacements = build_audit_replacements(
            args.client,
            args.month,
            args.year,
            args.prev_month,
            args.next_month,
        )
        template_placeholders = read_placeholders(services["slides"], template_id)
        audit = audit_placeholders(template_placeholders, set(replacements))
        print(json.dumps({"audit": audit, "replacement_count": len(replacements)}, indent=2))
        return 0

    if not args.spreadsheet:
        raise ValueError("--spreadsheet is required unless --audit-only is set")

    spreadsheet_id = extract_file_id(args.spreadsheet)

    campaigns = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.campaigns_sheet,
        args.client,
        month=args.month,
        year=args.year,
    )
    ads = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.ads_sheet,
        args.client,
        month=args.month,
        year=args.year,
    )
    checkpoints = validate_or_raise(campaigns)
    kpis = build_full_kpi_report(campaigns, ads)

    prev_campaigns = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.campaigns_sheet,
        args.client,
        month=args.prev_month,
        year=args.year,
    )
    prev_ads = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.ads_sheet,
        args.client,
        month=args.prev_month,
        year=args.year,
    )
    prev_checkpoints = validate_or_raise(prev_campaigns)
    prev_kpis = build_full_kpi_report(prev_campaigns, prev_ads)

    manual_inputs = read_manual_inputs(
        services["sheets"],
        spreadsheet_id,
        args.manual_inputs_sheet,
        args.client,
        args.month,
        args.year,
    )
    prev_manual_inputs = read_manual_inputs(
        services["sheets"],
        spreadsheet_id,
        args.manual_inputs_sheet,
        args.client,
        args.prev_month,
        args.year,
    )
    overrides = {
        "company_revenue": _manual_or_arg(manual_inputs, args, "company_revenue"),
        "ad_revenue": _manual_or_arg(manual_inputs, args, "ad_revenue"),
        "ad_cost": _manual_or_arg(manual_inputs, args, "ad_cost"),
        "prev_company_revenue": _manual_or_arg(
            prev_manual_inputs,
            args,
            "prev_company_revenue",
            manual_key="company_revenue",
        ),
        "prev_ad_revenue": _manual_or_arg(
            prev_manual_inputs,
            args,
            "prev_ad_revenue",
            manual_key="ad_revenue",
        ),
        "prev_ad_cost": _manual_or_arg(
            prev_manual_inputs,
            args,
            "prev_ad_cost",
            manual_key="ad_cost",
        ),
    }

    if not args.skip_kpi_output:
        write_kpi_output(services["sheets"], spreadsheet_id, kpis, sheet_name=args.kpi_output_sheet)

    if args.use_claude:
        insights = generate_insights(
            args.client,
            args.month,
            args.year,
            args.prev_month,
            kpis,
            overrides,
            media_buyer_notes=args.media_buyer_notes or str(manual_inputs.get("media_buyer_notes", "")),
            special_requests=args.special_requests or str(manual_inputs.get("special_requests", "")),
        )
        assert_insights_shape(insights)
        insights_mode = "claude"
    else:
        insights = build_fake_insights(kpis, args.client, args.month, args.year, args.next_month)
        insights_mode = "dry_run_fake"

    replacements = build_slides_replacements(
        args.client,
        args.month,
        args.year,
        args.prev_month,
        args.next_month,
        kpis,
        insights,
        overrides,
        prev_kpis=prev_kpis,
    )

    template_placeholders = read_placeholders(services["slides"], template_id)
    audit = audit_placeholders(template_placeholders, set(replacements))
    if args.audit_only:
        print(json.dumps({"audit": audit, "replacement_count": len(replacements)}, indent=2))
        return 0
    if audit["missing_values"]:
        raise ValueError(
            "Template has placeholders that this pipeline cannot fill: "
            + ", ".join(audit["missing_values"])
        )

    title = args.output_title or f"{args.client} {args.month} {args.year} Report"
    copied = copy_presentation(
        services["drive"],
        template_id,
        title,
        folder_id=args.output_folder_id or None,
    )
    occurrences = replace_placeholders(services["slides"], copied["id"], replacements)
    refreshed_charts = 0 if args.skip_chart_refresh else refresh_linked_sheets_charts(services["slides"], copied["id"])
    remaining = sorted(read_placeholders(services["slides"], copied["id"]))

    pdf_path = ""
    pptx_path = ""
    if args.export_pdf_path:
        pdf_path = str(export_presentation(services["drive"], copied["id"], args.export_pdf_path, PDF_MIME))
    if args.export_pptx_path:
        pptx_path = str(export_presentation(services["drive"], copied["id"], args.export_pptx_path, PPTX_MIME))

    thumbnail_urls = []
    if args.thumbnail_audit:
        thumbnail_urls = get_slide_thumbnail_urls(services["slides"], copied["id"], max_slides=12)

    status = "ok" if not remaining else "needs_review"
    if not args.skip_run_log:
        append_run_log(
            services["sheets"],
            spreadsheet_id,
            make_run_log_row(
                args.client,
                args.month,
                args.year,
                status,
                presentation_url=copied["webViewLink"],
                pdf_path=pdf_path,
                pptx_path=pptx_path,
                remaining_placeholders=remaining,
                validation={
                    "checkpoints": checkpoints,
                    "prev_checkpoints": prev_checkpoints,
                    "insights_mode": insights_mode,
                },
            ),
            sheet_name=args.run_log_sheet,
        )

    summary = {
        "status": status,
        "client": args.client,
        "period": f"{args.month} {args.year}",
        "presentation": copied,
        "replacement_occurrences": occurrences,
        "refreshed_linked_charts": refreshed_charts,
        "remaining_placeholders": remaining,
        "insights_mode": insights_mode,
        "template_audit": audit,
        "pdf_path": pdf_path,
        "pptx_path": pptx_path,
        "thumbnail_urls": thumbnail_urls,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

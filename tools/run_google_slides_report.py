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
from tools.generate_insights import INSIGHT_PROVIDER_CHOICES, generate_insights_with_provider
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
from tools.report_periods import resolve_reporting_window
from tools.report_insights import assert_insights_shape, build_fake_insights
from tools.report_replacements import build_audit_replacements
from tools.validate_data import validate_or_raise

PDF_MIME = "application/pdf"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
MIN_SUPPORTED_PYTHON = (3, 11)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Google Sheets -> Google Slides report pipeline.")
    parser.add_argument("--spreadsheet", default="", help="Google Sheet URL or ID")
    parser.add_argument("--template-presentation", required=True, help="Google Slides template URL or ID")
    parser.add_argument("--client", required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--prev-month", default="")
    parser.add_argument("--prev-year", type=int, default=None)
    parser.add_argument("--next-month", default="")
    parser.add_argument("--next-year", type=int, default=None)
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
    parser.add_argument(
        "--insights-provider",
        choices=sorted(INSIGHT_PROVIDER_CHOICES),
        default=os.environ.get("REPORT_INSIGHTS_PROVIDER", "deterministic"),
        help="Narrative provider. 'auto' tries Anthropic, then OpenAI, then deterministic fallback.",
    )
    parser.add_argument("--use-claude", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--audit-only", action="store_true", help="Audit template tokens without copying or editing.")
    parser.add_argument("--skip-run-log", action="store_true")
    parser.add_argument("--skip-kpi-output", action="store_true")
    parser.add_argument("--skip-chart-refresh", action="store_true")
    parser.add_argument("--thumbnail-audit", action="store_true", help="Print thumbnail URLs for quick visual checks.")
    parser.add_argument("--export-pdf-path", default="")
    parser.add_argument("--export-pptx-path", default="")
    return parser.parse_args()


def build_run_namespace(**overrides) -> argparse.Namespace:
    values = {
        "spreadsheet": "",
        "template_presentation": "",
        "client": "",
        "month": "",
        "year": 0,
        "prev_month": "",
        "prev_year": None,
        "next_month": "",
        "next_year": None,
        "campaigns_sheet": "Campaigns",
        "ads_sheet": "Ads",
        "manual_inputs_sheet": "Manual Inputs",
        "kpi_output_sheet": "KPI Output",
        "run_log_sheet": "Run Log",
        "output_folder_id": os.environ.get("GOOGLE_DRIVE_OUTPUT_FOLDER_ID", ""),
        "output_title": "",
        "company_revenue": None,
        "ad_revenue": None,
        "ad_cost": None,
        "prev_company_revenue": None,
        "prev_ad_revenue": None,
        "prev_ad_cost": None,
        "media_buyer_notes": "",
        "special_requests": "",
        "insights_provider": os.environ.get("REPORT_INSIGHTS_PROVIDER", "deterministic"),
        "use_claude": False,
        "audit_only": False,
        "skip_run_log": False,
        "skip_kpi_output": False,
        "skip_chart_refresh": False,
        "thumbnail_audit": False,
        "export_pdf_path": "",
        "export_pptx_path": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


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


def ensure_supported_python_version() -> None:
    if sys.version_info < MIN_SUPPORTED_PYTHON:
        wanted = ".".join(str(part) for part in MIN_SUPPORTED_PYTHON)
        current_info = tuple(sys.version_info[:3])
        current = ".".join(str(part) for part in current_info)
        raise RuntimeError(
            f"Python {wanted}+ is required for launch readiness. Current runtime is {current}. "
            "Upgrade the interpreter or run the container/CI image based on Python 3.11+."
        )


def resolve_requested_provider(args: argparse.Namespace) -> str:
    provider = getattr(args, "insights_provider", "deterministic")
    if getattr(args, "use_claude", False):
        if provider not in {"", "deterministic", "anthropic"}:
            raise ValueError("--use-claude cannot be combined with a non-Anthropic insights provider.")
        provider = "anthropic"
    normalized = (provider or "deterministic").strip().lower()
    if normalized not in INSIGHT_PROVIDER_CHOICES:
        raise ValueError(
            f"Unsupported insights provider {provider!r}. Expected one of {sorted(INSIGHT_PROVIDER_CHOICES)}."
        )
    return normalized


def validate_runtime_inputs(args: argparse.Namespace) -> None:
    if not args.audit_only and not args.spreadsheet:
        raise ValueError("--spreadsheet is required unless --audit-only is set")
    if args.audit_only:
        return
    provider = resolve_requested_provider(args)
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise EnvironmentError("ANTHROPIC_API_KEY is required when insights provider is 'anthropic'.")
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY", "").strip():
        raise EnvironmentError("OPENAI_API_KEY is required when insights provider is 'openai'.")


def run_report(args: argparse.Namespace, services: dict | None = None) -> dict:
    validate_runtime_inputs(args)
    window = resolve_reporting_window(
        args.month,
        args.year,
        prev_month=args.prev_month or None,
        prev_year=args.prev_year,
        next_month=args.next_month or None,
        next_year=args.next_year,
    )
    requested_provider = resolve_requested_provider(args)
    template_id = extract_file_id(args.template_presentation)
    services = services or build_workspace_services()

    if args.audit_only:
        replacements = build_audit_replacements(
            args.client,
            window.month,
            window.year,
            window.prev_month,
            window.next_month,
        )
        template_placeholders = read_placeholders(services["slides"], template_id)
        audit = audit_placeholders(template_placeholders, set(replacements))
        return {
            "status": "audit_ok",
            "client": args.client,
            "period": f"{window.month} {window.year}",
            "audit": audit,
            "replacement_count": len(replacements),
        }

    spreadsheet_id = extract_file_id(args.spreadsheet)

    campaigns = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.campaigns_sheet,
        args.client,
        month=window.month,
        year=window.year,
    )
    ads = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.ads_sheet,
        args.client,
        month=window.month,
        year=window.year,
    )
    checkpoints = validate_or_raise(campaigns)
    kpis = build_full_kpi_report(campaigns, ads)

    prev_campaigns = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.campaigns_sheet,
        args.client,
        month=window.prev_month,
        year=window.prev_year,
    )
    prev_ads = load_report_sheet(
        services["sheets"],
        spreadsheet_id,
        args.ads_sheet,
        args.client,
        month=window.prev_month,
        year=window.prev_year,
    )
    prev_checkpoints = validate_or_raise(prev_campaigns)
    prev_kpis = build_full_kpi_report(prev_campaigns, prev_ads)

    manual_inputs = read_manual_inputs(
        services["sheets"],
        spreadsheet_id,
        args.manual_inputs_sheet,
        args.client,
        window.month,
        window.year,
    )
    prev_manual_inputs = read_manual_inputs(
        services["sheets"],
        spreadsheet_id,
        args.manual_inputs_sheet,
        args.client,
        window.prev_month,
        window.prev_year,
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

    insights, used_provider = generate_insights_with_provider(
        requested_provider,
        client=args.client,
        month=window.month,
        year=window.year,
        prev_month=window.prev_month,
        prev_year=window.prev_year,
        kpis=kpis,
        user_overrides=overrides,
        media_buyer_notes=args.media_buyer_notes or str(manual_inputs.get("media_buyer_notes", "")),
        special_requests=args.special_requests or str(manual_inputs.get("special_requests", "")),
        deterministic_factory=lambda: build_fake_insights(
            kpis,
            args.client,
            window.month,
            window.year,
            window.next_month,
        ),
    )
    assert_insights_shape(insights)
    if requested_provider == "auto" and used_provider != "auto":
        insights_mode = f"auto->{used_provider}"
    else:
        insights_mode = used_provider

    replacements = build_slides_replacements(
        args.client,
        window.month,
        window.year,
        window.prev_month,
        window.next_month,
        kpis,
        insights,
        overrides,
        prev_kpis=prev_kpis,
    )

    template_placeholders = read_placeholders(services["slides"], template_id)
    audit = audit_placeholders(template_placeholders, set(replacements))
    if audit["missing_values"]:
        raise ValueError(
            "Template has placeholders that this pipeline cannot fill: "
            + ", ".join(audit["missing_values"])
        )

    output_folder_id = extract_file_id(args.output_folder_id) if args.output_folder_id else None

    title = args.output_title or f"{args.client} {window.month} {window.year} Report"
    copied = copy_presentation(
        services["drive"],
        template_id,
        title,
        folder_id=output_folder_id,
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
                window.month,
                window.year,
                status,
                presentation_url=copied["webViewLink"],
                pdf_path=pdf_path,
                pptx_path=pptx_path,
                remaining_placeholders=remaining,
                validation={
                    "checkpoints": checkpoints,
                    "prev_checkpoints": prev_checkpoints,
                    "requested_insights_provider": requested_provider,
                    "used_insights_provider": used_provider,
                    "prev_period": f"{window.prev_month} {window.prev_year}",
                },
            ),
            sheet_name=args.run_log_sheet,
        )

    return {
        "status": status,
        "client": args.client,
        "period": f"{window.month} {window.year}",
        "prev_period": f"{window.prev_month} {window.prev_year}",
        "presentation": copied,
        "spreadsheet_id": spreadsheet_id,
        "template_presentation_id": template_id,
        "replacement_occurrences": occurrences,
        "refreshed_linked_charts": refreshed_charts,
        "remaining_placeholders": remaining,
        "requested_insights_provider": requested_provider,
        "used_insights_provider": used_provider,
        "insights_mode": insights_mode,
        "template_audit": audit,
        "pdf_path": pdf_path,
        "pptx_path": pptx_path,
        "thumbnail_urls": thumbnail_urls,
    }


def main() -> int:
    args = parse_args()
    ensure_supported_python_version()
    summary = run_report(args)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

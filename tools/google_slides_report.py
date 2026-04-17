"""Google Slides template copying, placeholder replacement, and auditing."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tools.report_replacements import build_replacements

PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")


def build_slides_replacements(
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
    """Build formatted placeholder replacements for Google Slides."""
    replacements = build_replacements(
        client,
        month,
        year,
        prev_month,
        next_month,
        kpis,
        insights,
        user_overrides,
        prev_kpis=prev_kpis,
    )
    return {key: "" if value is None else str(value) for key, value in replacements.items()}


def copy_presentation(
    drive_service,
    template_presentation_id: str,
    title: str,
    folder_id: str | None = None,
) -> dict[str, str]:
    body: dict[str, Any] = {"name": title}
    if folder_id:
        body["parents"] = [folder_id]
    copied = (
        drive_service.files()
        .copy(
            fileId=template_presentation_id,
            body=body,
            fields="id, name, webViewLink",
        )
        .execute()
    )
    return {
        "id": copied["id"],
        "name": copied.get("name", title),
        "webViewLink": copied.get("webViewLink", ""),
    }


def make_replace_all_text_requests(replacements: dict[str, str]) -> list[dict]:
    """Create Slides API replaceAllText requests for every placeholder."""
    return [
        {
            "replaceAllText": {
                "containsText": {"text": placeholder, "matchCase": True},
                "replaceText": value,
            }
        }
        for placeholder, value in sorted(replacements.items())
    ]


def replace_placeholders(
    slides_service,
    presentation_id: str,
    replacements: dict[str, str],
    batch_size: int = 100,
) -> int:
    """Replace placeholders and return the total occurrence count reported by Slides."""
    requests = make_replace_all_text_requests(replacements)
    occurrences = 0
    for start in range(0, len(requests), batch_size):
        chunk = requests[start : start + batch_size]
        response = (
            slides_service.presentations()
            .batchUpdate(presentationId=presentation_id, body={"requests": chunk})
            .execute()
        )
        for reply in response.get("replies", []):
            occurrences += reply.get("replaceAllText", {}).get("occurrencesChanged", 0)
    return occurrences


def _collect_text_from_element(element: dict[str, Any], parts: list[str]) -> None:
    shape = element.get("shape", {})
    text = shape.get("text", {})
    for text_element in text.get("textElements", []):
        content = text_element.get("textRun", {}).get("content")
        if content:
            parts.append(content)

    table = element.get("table", {})
    for row in table.get("tableRows", []):
        for cell in row.get("tableCells", []):
            for text_element in cell.get("text", {}).get("textElements", []):
                content = text_element.get("textRun", {}).get("content")
                if content:
                    parts.append(content)

    for child in element.get("elementGroup", {}).get("children", []):
        _collect_text_from_element(child, parts)


def extract_placeholders_from_presentation(presentation: dict[str, Any]) -> set[str]:
    parts: list[str] = []
    for slide in presentation.get("slides", []):
        for element in slide.get("pageElements", []) or []:
            _collect_text_from_element(element, parts)
    return set(PLACEHOLDER_RE.findall("\n".join(parts)))


def read_placeholders(slides_service, presentation_id: str) -> set[str]:
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    return extract_placeholders_from_presentation(presentation)


def audit_placeholders(
    template_placeholders: set[str],
    available_replacements: set[str],
) -> dict[str, list[str]]:
    missing_values = sorted(template_placeholders - available_replacements)
    unused_values = sorted(available_replacements - template_placeholders)
    return {
        "template_placeholders": sorted(template_placeholders),
        "missing_values": missing_values,
        "unused_values": unused_values,
    }


def find_sheets_chart_object_ids(presentation: dict[str, Any]) -> list[str]:
    object_ids: list[str] = []
    for slide in presentation.get("slides", []):
        for element in slide.get("pageElements", []) or []:
            if "sheetsChart" in element and element.get("objectId"):
                object_ids.append(element["objectId"])
    return object_ids


def refresh_linked_sheets_charts(slides_service, presentation_id: str) -> int:
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    chart_ids = find_sheets_chart_object_ids(presentation)
    if not chart_ids:
        return 0
    requests = [{"refreshSheetsChart": {"objectId": object_id}} for object_id in chart_ids]
    slides_service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests},
    ).execute()
    return len(chart_ids)


def export_presentation(
    drive_service,
    presentation_id: str,
    output_path: str | Path,
    mime_type: str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = drive_service.files().export(fileId=presentation_id, mimeType=mime_type).execute()
    output_path.write_bytes(data)
    return output_path


def get_slide_thumbnail_urls(slides_service, presentation_id: str, max_slides: int | None = None) -> list[str]:
    presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
    urls: list[str] = []
    for slide in presentation.get("slides", [])[:max_slides]:
        page_id = slide.get("objectId")
        if not page_id:
            continue
        thumbnail = (
            slides_service.presentations()
            .pages()
            .getThumbnail(
                presentationId=presentation_id,
                pageObjectId=page_id,
                thumbnailProperties_mimeType="PNG",
                thumbnailProperties_thumbnailSize="MEDIUM",
            )
            .execute()
        )
        if thumbnail.get("contentUrl"):
            urls.append(thumbnail["contentUrl"])
    return urls

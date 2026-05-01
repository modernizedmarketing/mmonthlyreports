#!/usr/bin/env python3
"""Minimal internal web UI for triggering monthly report jobs."""
from __future__ import annotations

import json
import os
import sys
from html import escape
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.cloud_run_jobs import CloudRunJobLauncher
from tools.control_sheet import load_control_sheet_clients
from tools.google_workspace import build_workspace_services, extract_file_id
from tools.report_periods import default_reporting_window


def _read_body(environ) -> bytes:
    length = int(environ.get("CONTENT_LENGTH") or "0")
    return environ["wsgi.input"].read(length)


def _wants_json(environ) -> bool:
    accept = environ.get("HTTP_ACCEPT", "")
    content_type = environ.get("CONTENT_TYPE", "")
    return "application/json" in accept or "application/json" in content_type


def _parse_request_payload(environ) -> dict[str, str]:
    body = _read_body(environ)
    content_type = environ.get("CONTENT_TYPE", "")
    if "application/json" in content_type:
        raw = json.loads(body.decode("utf-8") or "{}")
        return {str(key): str(value) for key, value in raw.items() if value is not None}
    parsed = parse_qs(body.decode("utf-8"))
    return {key: values[0] for key, values in parsed.items() if values}


def _normalize_run_request(payload: dict[str, str]) -> dict[str, str]:
    run_mode = payload.get("run_mode", "all").strip().lower() or "all"
    if run_mode not in {"all", "one"}:
        raise ValueError("run_mode must be 'all' or 'one'.")
    client_key = payload.get("client_key", "").strip()
    if run_mode == "one" and not client_key:
        raise ValueError("client_key is required when run_mode is 'one'.")
    month = payload.get("month", "").strip()
    year = payload.get("year", "").strip()
    insights_provider = payload.get("insights_provider", "auto").strip().lower() or "auto"
    if not month or not year:
        raise ValueError("month and year are required.")
    return {
        "run_mode": run_mode,
        "client_key": client_key,
        "month": month,
        "year": year,
        "insights_provider": insights_provider,
    }


def _make_env_overrides(payload: dict[str, str]) -> dict[str, str]:
    return {
        "RUN_MODE": payload["run_mode"],
        "CLIENT_KEY": payload["client_key"],
        "REPORT_MONTH": payload["month"],
        "REPORT_YEAR": payload["year"],
        "INSIGHTS_PROVIDER": payload["insights_provider"],
    }


def render_dashboard_html(clients: list[dict], message: str = "", error: str = "") -> str:
    default_window = default_reporting_window()
    options = "\n".join(
        f'<option value="{escape(client["client_key"])}">{escape(client["client_name"])}</option>'
        for client in clients
    )
    message_html = f"<p style='color: green;'>{escape(message)}</p>" if message else ""
    error_html = f"<p style='color: #b00020;'>{escape(error)}</p>" if error else ""
    client_count = len(clients)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Monthly Report Control Panel</title>
    <style>
      body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 760px; padding: 0 1rem; background: #f7f3ec; color: #222; }}
      .card {{ background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 16px 50px rgba(0,0,0,0.08); }}
      label {{ display: block; margin-top: 1rem; font-weight: 600; }}
      input, select {{ width: 100%; padding: 0.75rem; margin-top: 0.35rem; border-radius: 10px; border: 1px solid #d7c9b8; }}
      .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
      button {{ margin-top: 1rem; background: #0a6c74; color: white; border: 0; border-radius: 999px; padding: 0.85rem 1.2rem; cursor: pointer; }}
      small {{ color: #555; }}
    </style>
  </head>
  <body>
    <div class="card">
      <h1>Monthly Report Control Panel</h1>
      <p>{client_count} active clients loaded from the master control sheet.</p>
      {message_html}
      {error_html}
      <form method="post" action="/runs">
        <label for="run_mode">Run mode</label>
        <select id="run_mode" name="run_mode">
          <option value="all">Run all clients</option>
          <option value="one">Run one client</option>
        </select>

        <label for="client_key">Client</label>
        <select id="client_key" name="client_key">
          <option value="">Select a client for single-run mode</option>
          {options}
        </select>

        <div class="row">
          <label for="month">Report month
            <input id="month" name="month" value="{escape(default_window.month)}">
          </label>
          <label for="year">Report year
            <input id="year" name="year" value="{default_window.year}">
          </label>
        </div>

        <label for="insights_provider">Insights provider</label>
        <select id="insights_provider" name="insights_provider">
          <option value="auto">auto</option>
          <option value="anthropic">anthropic</option>
          <option value="openai">openai</option>
          <option value="deterministic">deterministic</option>
        </select>
        <small>Use auto for real runs. It requires Anthropic or OpenAI and does not fall back to deterministic.</small>

        <button type="submit">Launch run</button>
      </form>
    </div>
  </body>
</html>"""


def build_app(client_loader: Callable[[], list[dict]], launcher) -> Callable:
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        if path == "/healthz":
            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"status":"ok"}']

        if path == "/" and method == "GET":
            try:
                clients = client_loader()
                body = render_dashboard_html(clients)
                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            except Exception as exc:
                body = render_dashboard_html([], error=str(exc))
                start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
            return [body.encode("utf-8")]

        if path == "/runs" and method == "POST":
            try:
                payload = _normalize_run_request(_parse_request_payload(environ))
                result = launcher.launch(_make_env_overrides(payload))
                response_payload = {
                    "status": "queued",
                    "operation": result.get("name", ""),
                    "requested": payload,
                }
                if _wants_json(environ):
                    start_response("202 Accepted", [("Content-Type", "application/json")])
                    return [json.dumps(response_payload).encode("utf-8")]
                clients = client_loader()
                body = render_dashboard_html(
                    clients,
                    message=f"Run queued successfully. Operation: {response_payload['operation']}",
                )
                start_response("202 Accepted", [("Content-Type", "text/html; charset=utf-8")])
                return [body.encode("utf-8")]
            except Exception as exc:
                if _wants_json(environ):
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [json.dumps({"status": "error", "error": str(exc)}).encode("utf-8")]
                try:
                    clients = client_loader()
                except Exception:
                    clients = []
                body = render_dashboard_html(clients, error=str(exc))
                start_response("400 Bad Request", [("Content-Type", "text/html; charset=utf-8")])
                return [body.encode("utf-8")]

        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Not found"]

    return app


def load_active_clients_for_dashboard() -> list[dict]:
    services = build_workspace_services()
    control_sheet = os.environ.get("MASTER_CONTROL_SHEET_ID", os.environ.get("CONTROL_SHEET_ID", "")).strip()
    if not control_sheet:
        raise EnvironmentError("MASTER_CONTROL_SHEET_ID or CONTROL_SHEET_ID must be set for the control panel.")
    clients = load_control_sheet_clients(
        services["sheets"],
        extract_file_id(control_sheet),
        sheet_name=os.environ.get("CONTROL_SHEET_CLIENTS_SHEET", "Clients"),
        active_only=True,
    )
    return [{"client_key": client.client_key, "client_name": client.client_name} for client in clients]


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    app = build_app(load_active_clients_for_dashboard, CloudRunJobLauncher())
    with make_server("0.0.0.0", port, app) as httpd:
        print(f"Monthly report control panel listening on :{port}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

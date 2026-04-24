"""Helpers for launching Cloud Run Jobs from the internal control panel."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import google.auth
from googleapiclient.discovery import build


CLOUD_PLATFORM_SCOPE = ["https://www.googleapis.com/auth/cloud-platform"]


@dataclass(frozen=True)
class CloudRunJobConfig:
    project_id: str
    region: str
    job_name: str
    container_name: str = ""


def load_cloud_run_job_config() -> CloudRunJobConfig:
    project_id = (
        os.environ.get("CLOUD_RUN_PROJECT")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or ""
    ).strip()
    region = os.environ.get("CLOUD_RUN_REGION", "").strip()
    job_name = os.environ.get("CLOUD_RUN_JOB_NAME", "").strip()
    container_name = os.environ.get("CLOUD_RUN_JOB_CONTAINER_NAME", "").strip()
    if not project_id or not region or not job_name:
        raise EnvironmentError(
            "CLOUD_RUN_PROJECT/GOOGLE_CLOUD_PROJECT, CLOUD_RUN_REGION, and CLOUD_RUN_JOB_NAME "
            "must be set to launch Cloud Run Jobs from the control panel."
        )
    return CloudRunJobConfig(
        project_id=project_id,
        region=region,
        job_name=job_name,
        container_name=container_name,
    )


def build_cloud_run_api(credentials=None):
    credentials = credentials or google.auth.default(scopes=CLOUD_PLATFORM_SCOPE)[0]
    return build("run", "v2", credentials=credentials, cache_discovery=False)


def job_resource_name(config: CloudRunJobConfig) -> str:
    return f"projects/{config.project_id}/locations/{config.region}/jobs/{config.job_name}"


class CloudRunJobLauncher:
    def __init__(self, job_config: CloudRunJobConfig | None = None, api=None):
        self.job_config = job_config or load_cloud_run_job_config()
        self.api = api or build_cloud_run_api()

    def _resolve_container_name(self) -> str:
        if self.job_config.container_name:
            return self.job_config.container_name

        job = self.api.projects().locations().jobs().get(name=job_resource_name(self.job_config)).execute()
        containers = job.get("template", {}).get("template", {}).get("containers", [])
        if not containers:
            return ""
        return containers[0].get("name", "")

    def launch(self, env_overrides: dict[str, str]) -> dict[str, Any]:
        container_name = self._resolve_container_name()
        container_override: dict[str, Any] = {
            "env": [{"name": key, "value": value} for key, value in sorted(env_overrides.items()) if value != ""]
        }
        if container_name:
            container_override["name"] = container_name
        body = {"overrides": {"containerOverrides": [container_override]}}
        return (
            self.api.projects()
            .locations()
            .jobs()
            .run(name=job_resource_name(self.job_config), body=body)
            .execute()
        )

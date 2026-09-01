from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from .settings import Settings


class AutopilotUnavailableError(RuntimeError):
    pass


class AutopilotClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.autopilot_base_url
        self.token = settings.autopilot_token

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def control_centre(self) -> dict[str, Any]:
        if not self.configured:
            raise AutopilotUnavailableError("GCP Autopilot bridge is not configured")
        try:
            response = httpx.get(
                f"{self.base_url}/v1/control-centre",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=35,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("control-centre response must be an object")
            artifact_hashes = {
                name: hashlib.sha256(
                    json.dumps(payload.get(name), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
                ).hexdigest()
                for name in ("plan", "predictions", "shadow_v42", "automation")
            }
            payload["source_provenance"] = {
                "schema_version": "external-artifact-v1",
                "source": "gcp-autopilot-read-only-bridge",
                "source_availability": "external_runtime_not_vendored",
                "bridge_url": self.base_url,
                "bridge_version": payload.get("bridge_version"),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "artifact_hashes": artifact_hashes,
            }
            return payload
        except (httpx.HTTPError, ValueError) as error:
            raise AutopilotUnavailableError("GCP Autopilot bridge is unavailable") from error

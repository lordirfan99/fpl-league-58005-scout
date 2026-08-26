from __future__ import annotations

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
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise AutopilotUnavailableError("GCP Autopilot bridge is unavailable") from error

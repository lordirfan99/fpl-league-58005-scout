from types import SimpleNamespace

from app.autopilot import AutopilotClient


class Response:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "bridge_version": "2.1.0",
            "writes_enabled": False,
            "plan": {"gw": 2},
            "predictions": [{"element": 1, "points": 5.2}],
            "shadow_v42": {"model_version": "competitive-v4.2-shadow"},
            "automation": {"status": "ok"},
        }


def test_control_centre_adds_immutable_external_artifact_hashes(monkeypatch) -> None:
    monkeypatch.setattr("app.autopilot.httpx.get", lambda *args, **kwargs: Response())
    settings = SimpleNamespace(autopilot_base_url="https://bridge.example", autopilot_token="secret")
    payload = AutopilotClient(settings).control_centre()
    provenance = payload["source_provenance"]
    assert provenance["schema_version"] == "external-artifact-v1"
    assert provenance["source_availability"] == "external_runtime_not_vendored"
    assert provenance["bridge_version"] == "2.1.0"
    assert set(provenance["artifact_hashes"]) == {"plan", "predictions", "shadow_v42", "automation"}
    assert all(len(value) == 64 for value in provenance["artifact_hashes"].values())
    assert payload["writes_enabled"] is False

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run_scheduled_task.py"
SPEC = importlib.util.spec_from_file_location("run_scheduled_task", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

client = TestClient(app)


def test_latest_final_gameweek_picks_highest_finished_and_data_checked(monkeypatch) -> None:
    events = [
        {"id": 1, "finished": True, "data_checked": True},
        {"id": 2, "finished": True, "data_checked": True},
        {"id": 3, "finished": True, "data_checked": False},  # played, bonus not confirmed
        {"id": 4, "finished": False, "data_checked": False},
    ]
    monkeypatch.setattr(MODULE, "_bootstrap_events", lambda: events)
    assert MODULE._latest_final_gameweek() == 2


def test_latest_final_gameweek_is_zero_before_any_gameweek_completes(monkeypatch) -> None:
    monkeypatch.setattr(MODULE, "_bootstrap_events", lambda: [{"id": 1, "finished": False, "data_checked": False}])
    assert MODULE._latest_final_gameweek() == 0


def test_finalizer_reuses_packaged_finalized_gameweek_before_uploading(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    monkeypatch.setattr(MODULE, "LEAGUES", (1, 2))
    for league in MODULE.LEAGUES:
        for kind in ("data", "compact"):
            path = tmp_path / "data" / f"gw7_league{league}_{kind}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
    journal = tmp_path / "data" / "journal" / MODULE.SEASON / "gw07.json"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text("{}", encoding="utf-8")

    class Blob:
        def exists(self) -> bool:
            return False

    class Bucket:
        def blob(self, _name: str) -> Blob:
            return Blob()

    commands: list[tuple[str, ...]] = []
    monkeypatch.setattr(MODULE, "_bucket", lambda: Bucket())
    monkeypatch.setattr(MODULE, "_run", lambda *command: commands.append(command))
    monkeypatch.setattr(MODULE, "_validate_gameweek", lambda _gameweek: None)
    monkeypatch.setattr(MODULE, "_upload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(MODULE, "task_decision_refresh", lambda *args, **kwargs: None)

    MODULE.task_finalize_gameweek(7)
    assert commands == []


def test_task_names_match_the_provisioned_cloud_run_jobs() -> None:
    parser_choices = {"fixtures", "capture-journal", "decision-refresh", "decision-final-window", "finalize-gameweek", "monitor"}
    # cloudbuild.api.yaml deploys one job per task arg.
    cloudbuild = (Path(__file__).resolve().parents[3] / "cloudbuild.api.yaml").read_text(encoding="utf-8")
    for task in parser_choices:
        assert f"--args={task}" in cloudbuild, task


def test_journal_export_still_serves_the_packaged_csv() -> None:
    response = client.get("/v1/journal/2026-27/export?filename=gameweeks.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "gameweek" in response.text.splitlines()[0].lower()


def test_unknown_journal_export_is_rejected() -> None:
    assert client.get("/v1/journal/2026-27/export?filename=secrets.json").status_code == 400

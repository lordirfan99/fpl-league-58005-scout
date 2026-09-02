"""Single entrypoint for the GCP Cloud Run scheduled tasks.

Replaces the GitHub Actions cron schedules (refresh-fixtures, capture-journal,
refresh-gameweek, monitor-production). The GitHub workflows are retained as
manual ``workflow_dispatch`` fallbacks.

Each task is invoked as a Cloud Run Job argument, e.g. ``run_scheduled_task.py
finalize-gameweek``. Finalized artifacts are published to the shared snapshot
bucket under ``snapshots/`` (the read API already resolves those first), so no
API redeploy is needed per gameweek.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

BUCKET = (os.getenv("FPL_SNAPSHOT_BUCKET") or os.getenv("FPL_JOURNAL_BUCKET") or "").strip()
API_URL = os.getenv("FPL_API_BASE_URL", "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").rstrip("/")
SITE_URL = os.getenv("FPL_SITE_URL", "https://fpl-scout-intelligence.netlify.app").rstrip("/")
LEAGUES = (58005, 131997)
SEASON = "2026-27"


def _bucket():
    from google.cloud import storage

    if not BUCKET:
        raise SystemExit("FPL_SNAPSHOT_BUCKET (or FPL_JOURNAL_BUCKET) is required")
    return storage.Client().bucket(BUCKET)


def _upload(local: Path, name: str, *, immutable: bool) -> None:
    blob = _bucket().blob(name)
    if immutable and blob.exists():
        print(f"immutable object already present, keeping: gs://{BUCKET}/{name}", flush=True)
        return
    kwargs = {"if_generation_match": 0} if immutable and not blob.exists() else {}
    blob.upload_from_string(local.read_bytes(), content_type="application/json", **kwargs)
    print(f"published gs://{BUCKET}/{name} ({local.stat().st_size} bytes)", flush=True)


def _run(*cmd: str) -> None:
    print("+", sys.executable, *cmd, flush=True)
    subprocess.run([sys.executable, *cmd], cwd=ROOT, check=True)


def _bootstrap_events() -> list[dict]:
    request = urllib.request.Request(
        "https://fantasy.premierleague.com/api/bootstrap-static/",
        headers={"User-Agent": "Fantasy-Scout-Tasks/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["events"]


def _official_bootstrap() -> dict:
    request = urllib.request.Request(
        "https://fantasy.premierleague.com/api/bootstrap-static/",
        headers={"User-Agent": "Fantasy-Scout-Tasks/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _official_fixtures(gameweek: int, bootstrap: dict) -> list[dict]:
    request = urllib.request.Request(
        f"https://fantasy.premierleague.com/api/fixtures/?event={gameweek}",
        headers={"User-Agent": "Fantasy-Scout-Tasks/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        fixtures = json.load(response)
    teams = {int(row["id"]): row.get("name", "—") for row in bootstrap.get("teams", [])}
    return [{
        **row, "team_h": teams.get(int(row.get("team_h") or 0), "—"),
        "team_a": teams.get(int(row.get("team_a") or 0), "—"),
    } for row in fixtures]


def _snapshot_for_gameweek(gameweek: int) -> dict | None:
    """Prefer immutable GCS snapshots, then the task-image recovery copy."""
    name = f"snapshots/gw{gameweek}_league{LEAGUES[0]}_data.json"
    try:
        return json.loads(_bucket().blob(name).download_as_text(encoding="utf-8"))
    except Exception:
        path = ROOT / "data" / f"gw{gameweek}_league{LEAGUES[0]}_data.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _planning_name(gameweek: int) -> str:
    return f"planning/{SEASON}/gw{gameweek:02d}/current.json"


def _write_json(name: str, payload: dict, *, immutable: bool = False) -> bool:
    blob = _bucket().blob(name)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if immutable and blob.exists():
        print(f"immutable object already present, keeping: gs://{BUCKET}/{name}", flush=True)
        return False
    kwargs = {"if_generation_match": 0} if immutable else {}
    blob.upload_from_string(encoded, content_type="application/json", **kwargs)
    return True


def _latest_final_gameweek() -> int:
    return max(
        (event["id"] for event in _bootstrap_events() if event.get("finished") and event.get("data_checked")),
        default=0,
    )


# --------------------------------------------------------------------------- tasks


def task_fixtures() -> None:
    _run("scripts/fetch_fixture_horizon.py")
    for name in ("bootstrap_cache.json", "fixtures_cache.json"):
        _upload(ROOT / "data" / name, f"snapshots/{name}", immutable=False)
    bootstrap = json.loads(_bucket().blob("snapshots/bootstrap_cache.json").download_as_text(encoding="utf-8"))
    assert bootstrap["_meta"]["source"] == "official-fpl-api/bootstrap-static", bootstrap.get("_meta")
    assert len(bootstrap["elements"]) >= 400, len(bootstrap["elements"])
    fixtures = json.loads(_bucket().blob("snapshots/fixtures_cache.json").download_as_text(encoding="utf-8"))
    assert fixtures["source"] == "official-fpl-api" and fixtures["fixture_count"] >= 300, fixtures.get("fixture_count")
    assert len(fixtures["content_sha256"]) == 64
    print("reference caches published and provenance verified", flush=True)


def task_capture_journal(gameweek: int | None) -> None:
    task_decision_refresh(final_window=True, gameweek=gameweek)


def task_decision_refresh(final_window: bool = False, gameweek: int | None = None) -> None:
    """Publish a deadline-safe plan using the latest final GW as its baseline."""
    from app.planning import build_artifact, freeze_payload, next_event

    bootstrap = _official_bootstrap()
    event = next((row for row in bootstrap.get("events", []) if int(row.get("id") or 0) == gameweek), None) if gameweek else next_event(bootstrap)
    if not event:
        print("no next FPL deadline is published", flush=True)
        return
    target = int(event["id"])
    deadline = datetime.fromisoformat(str(event["deadline_time"]).replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if final_window and not (deadline - timedelta(hours=2) <= now < deadline):
        print(f"GW{target} final planning window is closed", flush=True)
        return
    source = next((
        snapshot for candidate in range(target - 1, 0, -1)
        if (snapshot := _snapshot_for_gameweek(candidate)) is not None
    ), None)
    if source is None:
        print(f"GW{target} planning skipped: no finalized source snapshot", flush=True)
        return
    artifact = build_artifact(
        source_snapshot=source, target_event=event, bootstrap=bootstrap,
        fixtures=_official_fixtures(target, bootstrap), league_id=LEAGUES[0], team_id=2797967, now=now,
    )
    _write_json(_planning_name(target), artifact)
    print(f"GW{target} {artifact['packet_status']} decision plan published", flush=True)
    # Freeze exactly once in the last 15 minutes. The stored decision is
    # entirely pre-deadline and therefore safe for later journal analysis.
    if deadline - timedelta(minutes=15) <= now < deadline and artifact["quality_status"] == "valid":
        frozen = freeze_payload(artifact, season=SEASON, now=now)
        _write_json(f"journal-raw/{SEASON}/gw{target:02d}/predeadline.json", frozen, immutable=True)
        print(f"GW{target} pre-deadline decision frozen", flush=True)


def _validate_gameweek(gameweek: int) -> None:
    """Mirror the refresh-gameweek.yml 'Validate snapshot integrity' step."""
    for league in LEAGUES:
        full = json.loads((ROOT / "data" / f"gw{gameweek}_league{league}_data.json").read_text(encoding="utf-8"))
        compact = json.loads((ROOT / "data" / f"gw{gameweek}_league{league}_compact.json").read_text(encoding="utf-8"))
        assert full["gw"] == gameweek and full["league_id"] == league
        assert full["total_entries"] == len(full["competitors"]) > 0
        assert compact["total_entries"] == len(compact["competitors"]) == full["total_entries"]
        assert full.get("errors", 0) == 0, f"league {league}: fetch errors={full.get('errors')}"
        for manager in full["competitors"]:
            squad = manager.get("squad", [])
            assert len(squad) == 15, f"entry {manager.get('entry_id')} has {len(squad)} players"
            # Post auto-subs a completed GW has exactly 11 active picks; a Bench
            # Boost gameweek activates all 15.
            active = sum(1 for pick in squad if pick.get("multiplier", 0) > 0)
            assert active in (11, 15), f"entry {manager.get('entry_id')} has {active} active picks"
        print(f"GW{gameweek} league {league}: {len(full['competitors'])} valid managers", flush=True)


def task_finalize_gameweek(gameweek: int | None) -> None:
    gameweek = gameweek or _latest_final_gameweek()
    if not gameweek:
        print("no finished and data-checked gameweek is waiting for collection", flush=True)
        return
    required = [f"snapshots/gw{gameweek}_league{league}_{kind}.json" for league in LEAGUES for kind in ("data", "compact")]
    if all(_bucket().blob(name).exists() for name in required):
        print(f"GW{gameweek} snapshots already published; nothing to do", flush=True)
        return

    # The task image carries historical, git-finalized gameweeks as a recovery
    # source.  On the first scheduled run after this migration, publish those
    # immutable artifacts instead of trying to fetch them again: the collector
    # intentionally refuses to overwrite its packaged final files.
    local_required = [ROOT / "data" / name.removeprefix("snapshots/") for name in required]
    local_journal = ROOT / "data" / "journal" / SEASON / f"gw{gameweek:02d}.json"
    if all(path.is_file() for path in local_required) and local_journal.is_file():
        print(f"GW{gameweek} is already finalized in the task image; publishing to GCS", flush=True)
    else:
        _run("scripts/fetch_fixture_horizon.py")
        _run("scripts/fetch_gw_data_fixed.py", "--gw", str(gameweek), "--league", *map(str, LEAGUES), "--max", "3000", "--workers", "16")
        for league in LEAGUES:
            _run("scripts/generate_analysis.py", "--gw", str(gameweek), "--league", str(league))
        _run("scripts/build_gameweek_journal.py", "--gw", str(gameweek))
        _run("scripts/audit_model_backtest.py", "--season", SEASON, "--output", "reports/model-validation/2026-27.json")
    _validate_gameweek(gameweek)

    for league in LEAGUES:
        for kind in ("data", "compact"):
            name = f"gw{gameweek}_league{league}_{kind}.json"
            _upload(ROOT / "data" / name, f"snapshots/{name}", immutable=True)
    journal_dir = ROOT / "data" / "journal" / SEASON
    _upload(journal_dir / f"gw{gameweek:02d}.json", f"snapshots/journal/{SEASON}/gw{gameweek:02d}.json", immutable=True)
    for name in ("index.json", "exports/gameweeks.csv", "exports/players.csv", "exports/manifest.json", "exports/README.md"):
        _upload(journal_dir / name, f"snapshots/journal/{SEASON}/{name}", immutable=False)
    for name in ("bootstrap_cache.json", "fixtures_cache.json"):
        _upload(ROOT / "data" / name, f"snapshots/{name}", immutable=False)
    model_validation = ROOT / "reports" / "model-validation" / "2026-27.json"
    if model_validation.is_file():
        _upload(model_validation, f"snapshots/reports/model-validation/{SEASON}.json", immutable=False)
    print(f"GW{gameweek} finalized and published to gs://{BUCKET}/snapshots/", flush=True)
    # The completed snapshot is now the authoritative source for the next
    # deadline's plan; publish that candidate without waiting for the hourly run.
    task_decision_refresh()


def task_monitor() -> None:
    _run("scripts/monitor_production.py")
    _run(
        "scripts/load_smoke.py", f"{API_URL}/v1/leagues/58005/summary?page=1&page_size=50",
        "--requests", "20", "--concurrency", "4", "--p95-ms", "5000", "--byte-limit", "250000",
    )


def task_live_refresh() -> None:
    """Refresh the immutable live manifest without a Cloud Run Job minimum."""
    _run("scripts/refresh_live_leagues.py")
    _run(
        "scripts/load_smoke.py", f"{SITE_URL}/league",
        "--requests", "10", "--concurrency", "2", "--p95-ms", "8000", "--byte-limit", "1500000",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=["fixtures", "capture-journal", "decision-refresh", "decision-final-window", "finalize-gameweek", "monitor", "live-refresh"])
    parser.add_argument("--gw", type=int, default=None, help="Optional gameweek override")
    args = parser.parse_args()
    if args.task == "fixtures":
        task_fixtures()
    elif args.task == "capture-journal":
        task_capture_journal(args.gw)
    elif args.task == "decision-refresh":
        task_decision_refresh(gameweek=args.gw)
    elif args.task == "decision-final-window":
        task_decision_refresh(final_window=True, gameweek=args.gw)
    elif args.task == "finalize-gameweek":
        task_finalize_gameweek(args.gw)
    elif args.task == "live-refresh":
        task_live_refresh()
    else:
        task_monitor()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

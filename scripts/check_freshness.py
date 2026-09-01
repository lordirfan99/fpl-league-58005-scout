"""Weekly-refresh freshness watchdog.

Independent of the collectors and of GitHub's own "workflow failed" surface,
this check answers one question from the outside: *is the production API
serving data that is as fresh as it should be, given where we are in the
gameweek cycle?*

Exit code:
* ``0`` -- everything within tolerance (a mid-week "no finalized snapshot yet"
  gap is normal and does not fail the check; it is reported as a NOTE).
* ``1`` -- at least one hard freshness guarantee is broken. The calling
  workflow turns this into a Telegram alert.

Pure standard library so it runs anywhere with no install step.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

API = os.getenv("FPL_API_BASE_URL", "https://fpl-scout-api-bztsnhv3ea-uc.a.run.app").rstrip("/")
FPL_BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"

# Tolerances. Deliberately generous so the watchdog only fires on a genuinely
# stuck pipeline, never on ordinary schedule jitter.
CATALOG_MAX_AGE_HOURS = 6.0          # refresh-fixtures runs hourly; 6h == 5 misses
FINALIZE_GRACE_HOURS = 48.0          # hours after a GW deadline by which that GW
                                    # is reliably finished + data-checked, so a
                                    # missing finalized snapshot is a real fault


def _get_json(url: str, timeout: int = 60) -> dict:
    request = Request(url, headers={"User-Agent": "FPLScoutFreshness/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def main() -> int:
    now = datetime.now(timezone.utc)
    failures: list[str] = []
    notes: list[str] = []

    # 1. The API itself must be ready.
    try:
        health = _get_json(f"{API}/health")
    except Exception as error:  # noqa: BLE001 - any failure here is a page-worthy outage
        print(f"FAIL  /health unreachable: {error}")
        return 1
    if health.get("status") != "ok" or not health.get("readiness", {}).get("ready"):
        failures.append(f"/health not ready: {json.dumps(health.get('readiness', {}))[:300]}")

    catalog_age = health.get("readiness", {}).get("checks", {}).get("catalog", {}).get("freshness_hours")
    if catalog_age is None:
        failures.append("catalog freshness is unknown (bootstrap cache missing provenance)")
    elif catalog_age > CATALOG_MAX_AGE_HOURS:
        failures.append(
            f"official catalog is {catalog_age:.1f}h old (> {CATALOG_MAX_AGE_HOURS:.0f}h): "
            "refresh-fixtures is not publishing"
        )
    else:
        notes.append(f"catalog age {catalog_age:.1f}h OK")

    # 2. Where are we in the gameweek cycle?
    try:
        bootstrap = _get_json(FPL_BOOTSTRAP)
    except Exception as error:  # noqa: BLE001
        print(f"WARN  could not read official bootstrap ({error}); skipping cycle checks")
        bootstrap = {"events": []}
    events = bootstrap.get("events", [])
    prev_finished = [event for event in events if event.get("finished") and event.get("data_checked")]
    latest_final_event = max((int(event["id"]) for event in prev_finished), default=0)
    finalized_event = next(
        (event for event in prev_finished if int(event["id"]) == latest_final_event), None
    )

    # 3. Compare the latest finalized snapshot the API serves against that.
    try:
        recommendation = _get_json(f"{API}/v1/recommendations/current?league_id=58005")
        meta = recommendation.get("meta", {})
        snapshot_gw = int(meta.get("snapshot_gameweek") or 0)
        freshness_hours = meta.get("freshness_hours")
    except Exception as error:  # noqa: BLE001
        failures.append(f"/v1/recommendations/current failed: {error}")
        snapshot_gw = 0
        freshness_hours = None

    try:
        journal = _get_json(f"{API}/v1/journal")
        archived = {int(row.get("gameweek") or 0) for row in journal.get("gameweeks", [])}
    except Exception as error:  # noqa: BLE001
        failures.append(f"/v1/journal failed: {error}")
        archived = set()

    if latest_final_event:
        # Measure the grace period from the GW which is missing its finalized
        # snapshot. Once it is data-checked, the catalog may already identify
        # the following GW as current; using that deadline would defer alerts
        # by almost a full gameweek.
        deadline = _parse_iso((finalized_event or {}).get("deadline_time"))
        hours_since_finalized_deadline = (now - deadline).total_seconds() / 3600 if deadline else None

        snapshot_is_behind = snapshot_gw < latest_final_event
        journal_is_behind = latest_final_event not in archived

        # Only escalate to a failure once enough time has passed that the GW is
        # unambiguously done. Before that, a lag is the expected Fri->Sun gap.
        past_grace = (
            hours_since_finalized_deadline is None
            or hours_since_finalized_deadline > FINALIZE_GRACE_HOURS
        )
        if (snapshot_is_behind or journal_is_behind) and past_grace:
            failures.append(
                f"GW{latest_final_event} is finished + data-checked but the API still serves "
                f"snapshot GW{snapshot_gw} (journal has {sorted(archived) or 'nothing'}): "
                "refresh-gameweek is stuck"
            )
        elif snapshot_is_behind or journal_is_behind:
            notes.append(
                f"GW{latest_final_event} finalization pending (normal mid-week gap; "
                f"{hours_since_finalized_deadline:.0f}h since deadline)"
                if hours_since_finalized_deadline is not None
                else f"GW{latest_final_event} finalization pending"
            )
        else:
            notes.append(f"finalized snapshot up to GW{snapshot_gw} OK")

    if freshness_hours is not None:
        notes.append(f"recommendation snapshot age {freshness_hours:.1f}h")

    for note in notes:
        print(f"NOTE  {note}")
    for failure in failures:
        print(f"FAIL  {failure}")

    if failures:
        print(f"\n{len(failures)} freshness guarantee(s) broken.")
        return 1
    print("\nAll freshness guarantees within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

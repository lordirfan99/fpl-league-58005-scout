from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .autopilot import AutopilotClient, AutopilotUnavailableError
from .league_registry import LeagueRegistry
from .recommendations import MODEL_VERSION, build_recommendations, cohort_summary, elite_managers
from .repository import SnapshotNotFoundError, SnapshotRepository
from .schemas import (
    ApiMeta,
    CatalogResponse,
    EliteResponse,
    IntegrationStatus,
    LeagueResponse,
    RecommendationResponse,
    TeamResponse,
)
from .settings import settings
from .validation import snapshot_quality


app = FastAPI(
    title="Fantasy Scout Intelligence API",
    version="4.0.0",
    description="Stable read API for the FPL dashboard and recommendation engine.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
repository = SnapshotRepository(settings.data_dir, settings.snapshot_bucket)
league_registry = LeagueRegistry(settings.data_dir)
autopilot = AutopilotClient(settings)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok", "service": "fpl-scout-api", "version": app.version,
        "competitive_model": MODEL_VERSION, "execution_authority": "telegram",
        "dashboard_writes_enabled": False,
        "shared_snapshots": bool(settings.snapshot_bucket),
    }


@app.post("/internal/v1/snapshots/{filename}")
async def publish_snapshot(
    filename: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str | int]:
    """Ingest a VM-produced read-only snapshot into the private GCS store."""
    expected = settings.autopilot_token
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid snapshot publisher token")
    if not settings.snapshot_bucket:
        raise HTTPException(status_code=503, detail="Shared snapshot bucket is not configured")
    if filename not in {"bootstrap_cache.json", "fixtures_cache.json"} and not (
        filename.startswith("gw") and filename.endswith("_data.json") and filename.replace("_", "").replace(".", "").isalnum()
    ):
        raise HTTPException(status_code=400, detail="Invalid snapshot filename")
    body = await request.body()
    if len(body) > 5_000_000:
        raise HTTPException(status_code=413, detail="Snapshot exceeds 5 MB limit")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Snapshot is not valid JSON") from error
    if filename.startswith("gw"):
        quality, issues = snapshot_quality(payload)
        if quality != "valid":
            raise HTTPException(status_code=422, detail={"quality": quality, "issues": issues[:10]})
        if int(payload.get("gw") or 0) <= 0 or not payload.get("competitors"):
            raise HTTPException(status_code=422, detail="Snapshot has no gameweek competitors")
    if repository._bucket is None:
        raise HTTPException(status_code=503, detail="GCS repository is unavailable")
    blob = repository._bucket.blob(f"snapshots/{filename}")
    blob.upload_from_string(json.dumps(payload, separators=(",", ":")), content_type="application/json")
    repository._remote_cache.pop(filename, None)
    return {"status": "published", "filename": filename, "bytes": len(body)}


@app.get("/v1/me")
def me() -> dict[str, int]:
    return {
        "team_id": settings.my_team_id,
        "default_league_id": settings.default_league_id,
        "current_gameweek": _current_gameweek(),
    }


@app.get("/v1/me/team", response_model=TeamResponse)
def my_team(
    league_id: int = Query(default=settings.default_league_id, gt=0),
    gw: int | None = Query(default=None, ge=1, le=38),
) -> TeamResponse:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    manager = next((item for item in snapshot.get("competitors", []) if item.get("entry_id") == settings.my_team_id), None)
    if manager is None:
        raise HTTPException(status_code=404, detail=f"Team {settings.my_team_id} is not in league {league_id} for GW{gw}")
    return TeamResponse(
        meta=_meta(snapshot),
        league_id=league_id,
        gameweek=gw,
        manager=manager,
        fixtures=repository.fixtures(min(gw + 1, 38)),
    )


@app.get("/v1/leagues/registry")
def league_registry_list() -> dict:
    """Return the shared tracked-league registry used by all clients."""
    registry = league_registry.read()
    return {
        "version": registry["version"],
        "max_active": registry["max_active"],
        "leagues": registry["leagues"],
    }


@app.get("/v1/leagues/{league_id}", response_model=LeagueResponse)
def league(league_id: int, gw: int | None = Query(default=None, ge=1, le=38)) -> LeagueResponse:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    managers = sorted(snapshot.get("competitors", []), key=lambda item: item.get("league_rank") or 10**12)
    declared_count = int(snapshot.get("total_entries") or len(managers))
    return LeagueResponse(
        meta=_meta(snapshot), league_id=league_id, gameweek=gw, count=len(managers),
        declared_count=declared_count,
        hydration_percent=round(len(managers) / max(1, declared_count) * 100, 1),
        managers=managers,
    )


@app.get("/v1/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    bootstrap = repository.bootstrap()
    return CatalogResponse(
        meta=ApiMeta(source="official-fpl-cache"),
        players=bootstrap.get("elements", []),
        teams=bootstrap.get("teams", []),
        events=bootstrap.get("events", []),
    )


@app.get("/v1/fixtures")
def fixtures(
    from_gw: int = Query(ge=1, le=38),
    to_gw: int = Query(ge=1, le=38),
) -> dict:
    if to_gw < from_gw or to_gw - from_gw > 9:
        raise HTTPException(status_code=400, detail="Fixture horizon must be between one and ten gameweeks")
    return {
        "from_gameweek": from_gw,
        "to_gameweek": to_gw,
        "gameweeks": repository.fixture_horizon(from_gw, to_gw),
    }


@app.get("/v1/elite/{gw}", response_model=EliteResponse)
def elite(
    gw: int,
    league_id: int = Query(default=settings.default_league_id, gt=0),
    percentile: int = Query(default=5, ge=1, le=25),
) -> EliteResponse:
    snapshot = _league_or_404(league_id, gw)
    cohort = elite_managers(
        snapshot.get("competitors", []),
        percentile,
        population_size=snapshot.get("population_size") or snapshot.get("total_entries"),
    )
    ownership, captaincy = cohort_summary(cohort)
    average = sum(item.get("gw_points", 0) for item in cohort) / max(1, len(cohort))
    return EliteResponse(
        meta=_meta(snapshot), league_id=league_id, gameweek=gw, percentile=percentile,
        count=len(cohort), average_points=round(average, 1), managers=cohort,
        ownership=ownership, captaincy=captaincy,
    )


@app.get("/v1/recommendations/current", response_model=RecommendationResponse)
def recommendations(
    league_id: int = Query(default=settings.default_league_id, gt=0),
    gw: int | None = Query(default=None, ge=1, le=38),
) -> RecommendationResponse:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    managers = snapshot.get("competitors", [])
    manager = next((item for item in managers if item.get("entry_id") == settings.my_team_id), None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Configured team is not present in this snapshot")
    result = build_recommendations(
        manager,
        managers,
        repository.bootstrap(),
        repository.fixtures(min(gw + 1, 38)),
        population_size=snapshot.get("population_size") or snapshot.get("total_entries"),
        gameweek=gw,
    )
    return RecommendationResponse(
        meta=_meta(snapshot), league_id=league_id, gameweek=gw, team_id=settings.my_team_id,
        disclaimer="Decision support only. Verify late team news before approving any FPL action.",
        **result,
    )


@app.get("/v1/integration/status", response_model=IntegrationStatus)
def integration_status() -> IntegrationStatus:
    missing = []
    if not settings.telegram_configured:
        missing.extend(["stable HTTPS webhook", "Telegram allowed user ID", "webhook secret"])
    return IntegrationStatus(
        configured=settings.telegram_configured,
        mode="approval" if settings.telegram_configured else "disconnected",
        bot_name=settings.telegram_bot_name,
        approvals_enabled=settings.telegram_configured,
        missing=missing,
    )


@app.get("/v1/autopilot/status")
def autopilot_status() -> dict:
    return {
        "configured": autopilot.configured,
        "mode": "read_only" if autopilot.configured else "disconnected",
        "execution_authority": "telegram",
        "dashboard_writes_enabled": False,
    }


@app.get("/v1/autopilot/control-centre")
def autopilot_control_centre() -> dict:
    try:
        return autopilot.control_centre()
    except AutopilotUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def _league_or_404(league_id: int, gw: int) -> dict:
    try:
        return repository.league(league_id, gw)
    except SnapshotNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"No snapshot for league {league_id}, GW{gw}") from error


def _meta(snapshot: dict) -> ApiMeta:
    raw_snapshot_at = snapshot.get("fetched_at")
    snapshot_at = None
    if raw_snapshot_at:
        try:
            snapshot_at = datetime.fromisoformat(str(raw_snapshot_at).replace("Z", "+00:00"))
            if snapshot_at.tzinfo is None:
                snapshot_at = snapshot_at.replace(tzinfo=timezone.utc)
        except ValueError:
            snapshot_at = None
    freshness_hours = None
    if snapshot_at is not None:
        freshness_hours = round((datetime.now(timezone.utc) - snapshot_at).total_seconds() / 3600, 2)
    stale = freshness_hours is None or freshness_hours > 12
    quality_status, quality_issues = snapshot_quality(snapshot)
    return ApiMeta(
        run_id=snapshot.get("run_id"), source="snapshot", snapshot_at=snapshot_at,
        stale=stale, freshness_hours=freshness_hours,
        snapshot_gameweek=int(snapshot.get("gw")) if snapshot.get("gw") is not None else None,
        quality_status=quality_status, quality_issues=quality_issues,
    )


@app.get("/v1/decision/current")
def decision_current(
    league_id: int = Query(default=settings.default_league_id, gt=0),
    gw: int | None = Query(default=None, ge=1, le=38),
) -> dict:
    """Return the single decision packet shared by Telegram and the dashboard.

    The API never executes FPL writes.  When the read-only autopilot bridge has
    a matching pending plan, its exact lineup/transfer packet is embedded;
    otherwise the response remains a non-executable V4 diagnostic packet.
    """
    gw = gw or _current_gameweek()
    bridge: dict = {}
    if autopilot.configured:
        try:
            bridge = autopilot.control_centre()
        except AutopilotUnavailableError:
            bridge = {}
    plan = bridge.get("plan") if isinstance(bridge, dict) else None
    if not isinstance(plan, dict) or int(plan.get("gw") or -1) != gw:
        plan = None
    plan_is_bound_v4 = bool(
        isinstance(plan, dict)
        and plan.get("model_version") == MODEL_VERSION
        and plan.get("plan_id")
        and plan.get("input_fp")
    )
    plan_is_v4 = plan_is_bound_v4 and plan.get("status") == "pending"
    plan_is_applied = plan_is_bound_v4 and plan.get("status") == "executed"
    try:
        recommendation = recommendations(league_id=league_id, gw=gw).model_dump(mode="json")
    except HTTPException as error:
        if error.status_code != 404:
            raise
        # Before the deadline, current-GW opponent picks cannot exist yet. A
        # fully bound V4 plan from the read-only bridge is still canonical;
        # competitor context remains neutral until the locked snapshot lands.
        now = datetime.now(timezone.utc).isoformat()
        if plan_is_v4 or plan_is_applied:
            packet_body = {"league_id": league_id, "gameweek": gw, "plan": plan}
            decision_id = hashlib.sha256(
                json.dumps(packet_body, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            return {
                "decision_id": decision_id,
                "model_version": MODEL_VERSION,
                "league_id": league_id,
                "gameweek": gw,
                "generated_at": plan.get("generated_at") or now,
                "meta": {"source": "autopilot_bridge", "stale": False,
                         "quality_status": "valid", "quality_issues": [],
                         "snapshot_gameweek": gw},
                "competitive": {"model_version": MODEL_VERSION, "phase": "MATCH",
                                 "phase_reason": "Canonical V4 plan; current opponent picks are not locked yet.",
                                 "alignment": 0, "target_alignment": 82},
                "plan": plan,
                "packet_status": "valid" if plan_is_v4 else "applied",
                "executable": plan_is_v4,
                "execution_authority": "telegram",
                "writes_enabled": False,
                "disclaimer": "Decision packet is read-only; Telegram performs final live validation and execution.",
            }
        return {
            "decision_id": hashlib.sha256(f"{league_id}:{gw}:safe_hold".encode()).hexdigest(),
            "model_version": MODEL_VERSION,
            "league_id": league_id,
            "gameweek": gw,
            "generated_at": now,
            "meta": {"source": "snapshot", "stale": True, "quality_status": "unknown",
                     "quality_issues": ["missing_gameweek_snapshot"], "snapshot_gameweek": gw},
            "competitive": {"model_version": MODEL_VERSION, "phase": "MATCH",
                             "phase_reason": "Waiting for the current gameweek snapshot.",
                             "alignment": 0, "target_alignment": 82},
            "plan": None,
            "packet_status": "safe_hold",
            "executable": False,
            "execution_authority": "telegram",
            "writes_enabled": False,
            "disclaimer": "No executable decision exists until the current FPL snapshot is ingested.",
        }
    # A competitive context without a complete, bound plan is not a live
    # decision.  Expose that state explicitly so clients cannot mistake a
    # diagnostic/legacy bridge payload for an executable recommendation.
    packet_status = "valid" if plan_is_v4 else ("applied" if plan_is_applied else "safe_hold")
    packet_body = {
        "league_id": league_id,
        "gameweek": gw,
        "competitive": recommendation["competitive"],
        "plan": plan,
        "packet_status": packet_status,
    }
    decision_id = hashlib.sha256(json.dumps(packet_body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        **recommendation,
        "decision_id": decision_id,
        "model_version": MODEL_VERSION,
        "league_id": league_id,
        "gameweek": gw,
        "generated_at": recommendation["meta"].get("generated_at"),
        "meta": recommendation["meta"],
        "competitive": recommendation["competitive"],
        "plan": plan,
        "packet_status": packet_status,
        "executable": plan_is_v4,
        "execution_authority": "telegram",
        "writes_enabled": False,
        "disclaimer": "Decision packet is read-only; Telegram performs final live validation and execution.",
    }


def _current_gameweek() -> int:
    events = repository.bootstrap().get("events", [])
    current = next((event for event in events if event.get("is_current")), None)
    if current:
        return int(current["id"])
    next_event = next((event for event in events if event.get("is_next")), None)
    if next_event:
        return max(1, int(next_event["id"]) - 1)
    finished = [int(event["id"]) for event in events if event.get("finished")]
    return max(finished, default=1)

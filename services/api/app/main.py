from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .autopilot import AutopilotClient, AutopilotUnavailableError
from .recommendations import build_recommendations, cohort_summary, elite_managers
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


app = FastAPI(
    title="Fantasy Scout Intelligence API",
    version="1.0.0",
    description="Stable read API for the FPL dashboard and recommendation engine.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
repository = SnapshotRepository(settings.data_dir)
autopilot = AutopilotClient(settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fpl-scout-api", "version": app.version}


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
        population_size=snapshot.get("total_entries"),
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
        population_size=snapshot.get("total_entries"),
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
    stale = snapshot_at is None or (datetime.now(timezone.utc) - snapshot_at).total_seconds() > 12 * 60 * 60
    return ApiMeta(source="snapshot", snapshot_at=snapshot_at, stale=stale)


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

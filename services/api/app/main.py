from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import re
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from .autopilot import AutopilotClient, AutopilotUnavailableError
from .league_registry import LeagueRegistry
from . import live_fpl
from .recommendations import MODEL_VERSION, build_recommendations, cohort_summary, elite_managers
from .projection_types import PROJECTION_VERSION
from .projections import build_projections
from .multiweek_optimizer import MultiWeekContext, OPTIMIZER_VERSION, optimize_multiweek_transfers
from .repository import ArtifactIntegrityError, SnapshotNotFoundError, SnapshotRepository
from .schemas import (
    ApiMeta,
    CatalogResponse,
    EliteResponse,
    IntegrationStatus,
    LeagueResponse,
    LeagueSummaryResponse,
    Manager,
    ManagerSummary,
    ProjectionResponse,
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
SEASON_PATTERN = re.compile(r"^20\d{2}-\d{2}$")


@app.middleware("http")
async def structured_request_log(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception as error:
        print(json.dumps({
            "level": "error", "message": "request_failed", "request_id": request_id,
            "method": request.method, "path": request.url.path,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "error_type": type(error).__name__,
        }), flush=True)
        raise
    response.headers["x-request-id"] = request_id
    response.headers["server-timing"] = f'app;dur={(time.perf_counter() - started) * 1000:.2f}'
    print(json.dumps({
        "level": "info", "message": "request_complete", "request_id": request_id,
        "method": request.method, "path": request.url.path, "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }), flush=True)
    return response


@app.get("/health")
def health() -> dict:
    readiness = _readiness()
    return {
        "status": "ok" if readiness["ready"] else "degraded", "service": "fpl-scout-api", "version": app.version,
        "revision": settings.git_revision, "build_time": settings.build_time,
        "competitive_model": MODEL_VERSION, "execution_authority": "telegram",
        "dashboard_writes_enabled": False,
        "shared_snapshots": bool(settings.snapshot_bucket),
        "readiness": readiness,
    }


@app.get("/ready")
def ready() -> JSONResponse:
    payload = _readiness()
    return JSONResponse(payload, status_code=200 if payload["ready"] else 503)


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
    # Identity is used by the web client to select the current live GW. Keep
    # it on the official FPL event feed, not on the latest finalized archive.
    current = live_fpl.current_gameweek()
    return {
        "team_id": settings.my_team_id,
        "default_league_id": settings.default_league_id,
        "current_gameweek": current,
    }


@app.get("/v1/live/team")
def live_team(
    gw: int | None = Query(default=None, ge=1, le=38),
    league_id: int | None = Query(default=settings.default_league_id, gt=0),
) -> dict:
    """Return the current public FPL team state with a short server cache.

    Live data is deliberately separate from snapshot-backed endpoints. It is
    suitable for the dashboard's current-week display, but never for journal
    records or completed-gameweek analysis.
    """
    target = gw or live_fpl.current_gameweek()
    try:
        return live_fpl.team(settings.my_team_id, target, league_id)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Official FPL live data unavailable: {error}") from error


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
    quality_status, quality_issues = snapshot_quality(snapshot)
    if quality_status != "valid":
        # Live/in-progress collector output may exist before it satisfies the
        # stable LeagueResponse contract. Do not let response-model validation
        # turn that expected provisional state into an opaque HTTP 500.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "snapshot_not_finalized",
                "league_id": league_id,
                "gameweek": gw,
                "quality_status": quality_status,
                "quality_issues": quality_issues[:10],
            },
        )
    raw_managers = sorted(snapshot.get("competitors", []), key=lambda item: item.get("league_rank") or 10**12)
    try:
        managers = [Manager.model_validate(item) for item in raw_managers]
    except ValidationError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "snapshot_not_finalized",
                "league_id": league_id,
                "gameweek": gw,
                "quality_status": "invalid",
                "quality_issues": [
                    f"schema:{'.'.join(str(part) for part in issue['loc'])}:{issue['type']}"
                    for issue in error.errors(include_input=False)[:10]
                ],
            },
        ) from error
    declared_count = int(snapshot.get("total_entries") or len(managers))
    return LeagueResponse(
        meta=_meta(snapshot), league_id=league_id, gameweek=gw, count=len(managers),
        declared_count=declared_count,
        hydration_percent=round(len(managers) / max(1, declared_count) * 100, 1),
        managers=managers,
    )


@app.get("/v1/leagues/{league_id}/summary", response_model=LeagueSummaryResponse)
def league_summary(
    league_id: int,
    gw: int | None = Query(default=None, ge=1, le=38),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=10, le=100),
    q: str = Query(default="", max_length=80),
) -> LeagueSummaryResponse:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    quality_status, quality_issues = snapshot_quality(snapshot)
    if quality_status != "valid":
        raise HTTPException(status_code=409, detail={
            "code": "snapshot_not_finalized", "league_id": league_id, "gameweek": gw,
            "quality_status": quality_status, "quality_issues": quality_issues[:10],
        })
    try:
        summaries = [ManagerSummary.model_validate(row) for row in sorted(
            snapshot.get("competitors", []), key=lambda item: item.get("league_rank") or 10**12
        )]
    except ValidationError as error:
        raise HTTPException(status_code=409, detail={
            "code": "snapshot_not_finalized", "league_id": league_id, "gameweek": gw,
            "quality_status": "invalid", "quality_issues": [
                f"schema:{'.'.join(str(part) for part in issue['loc'])}:{issue['type']}"
                for issue in error.errors(include_input=False)[:10]
            ],
        }) from error
    term = q.strip().casefold()
    filtered = [row for row in summaries if not term or term in (
        f"{row.entry_name} {row.player_name} {row.entry_id} {row.league_rank}".casefold()
    )]
    pages = max(1, math.ceil(len(filtered) / page_size))
    if page > pages:
        page = pages
    start = (page - 1) * page_size
    mine = next((row for row in summaries if row.entry_id == settings.my_team_id), None)
    return LeagueSummaryResponse(
        meta=_meta(snapshot), league_id=league_id, gameweek=gw, total=len(summaries),
        filtered_total=len(filtered), page=page, page_size=page_size, pages=pages, query=q.strip(),
        average_gameweek_points=round(sum(row.gw_points for row in summaries) / max(1, len(summaries)), 1),
        leader=summaries[0] if summaries else None, manager=mine,
        managers=filtered[start:start + page_size],
    )


@app.get("/v1/leagues/{league_id}/directory")
def league_directory(
    league_id: int,
    gw: int | None = Query(default=None, ge=1, le=38),
) -> dict:
    """Compact manager picker data; intentionally excludes every squad."""
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    quality_status, quality_issues = snapshot_quality(snapshot)
    if quality_status != "valid":
        raise HTTPException(status_code=409, detail={
            "code": "snapshot_not_finalized", "quality_status": quality_status,
            "quality_issues": quality_issues[:10], "gameweek": gw,
        })
    try:
        managers = [ManagerSummary.model_validate(row).model_dump() for row in sorted(
            snapshot.get("competitors", []), key=lambda item: item.get("league_rank") or 10**12
        )]
    except ValidationError as error:
        raise HTTPException(status_code=409, detail={
            "code": "snapshot_not_finalized", "league_id": league_id, "gameweek": gw,
            "quality_status": "invalid", "quality_issues": [
                f"schema:{'.'.join(str(part) for part in issue['loc'])}:{issue['type']}"
                for issue in error.errors(include_input=False)[:10]
            ],
        }) from error
    return {"meta": _meta(snapshot).model_dump(mode="json"), "league_id": league_id,
            "gameweek": gw, "count": len(managers), "managers": managers}


@app.get("/v1/leagues/{league_id}/managers/{entry_id}", response_model=Manager)
def league_manager(
    league_id: int,
    entry_id: int,
    gw: int | None = Query(default=None, ge=1, le=38),
) -> Manager:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    row = next((item for item in snapshot.get("competitors", []) if int(item.get("entry_id") or 0) == entry_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Manager {entry_id} is not in league {league_id} for GW{gw}")
    try:
        return Manager.model_validate(row)
    except ValidationError as error:
        raise HTTPException(status_code=409, detail={"code": "snapshot_not_finalized", "gameweek": gw}) from error


@app.get("/v1/catalog", response_model=CatalogResponse)
def catalog() -> CatalogResponse:
    bootstrap = repository.bootstrap()
    return CatalogResponse(
        meta=_bootstrap_meta(bootstrap),
        players=bootstrap.get("elements", []),
        teams=bootstrap.get("teams", []),
        events=bootstrap.get("events", []),
    )


@app.get("/v1/projections/current", response_model=ProjectionResponse)
def projections_current(
    gw: int | None = Query(default=None, ge=1, le=38),
) -> ProjectionResponse:
    """Return ownership-independent V5 laboratory projections.

    This endpoint is deliberately separate from production recommendations and
    the Telegram execution route.  Its candidate universe is the full official
    FPL catalogue, including players no tracked manager owns.
    """
    gw = gw or _current_gameweek()
    target_gw = min(gw + 1, 38)
    bootstrap = repository.bootstrap()
    rows = build_projections(bootstrap, repository.fixtures(target_gw))
    return ProjectionResponse(
        meta=_bootstrap_meta(
            bootstrap, source="projection-v5-lab", model_version=PROJECTION_VERSION,
            feature_version="v5-official-fpl-components-1",
        ),
        gameweek=target_gw,
        projection_version=PROJECTION_VERSION,
        players=[row.to_dict() for row in rows],
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


def _journal_season(value: str) -> str:
    if not SEASON_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Season must use YYYY-YY format")
    return value


@app.get("/v1/journal")
def journal_index(season: str = Query(default="2026-27")) -> dict:
    season = _journal_season(season)
    try:
        return repository.journal_index(season)
    except SnapshotNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"No journal for season {season}") from error
    except ArtifactIntegrityError as error:
        raise HTTPException(status_code=409, detail={"code": "journal_integrity_failure", "message": str(error)}) from error


@app.get("/v1/journal/{season}/gw/{gameweek}")
def journal_gameweek(season: str, gameweek: int) -> dict:
    season = _journal_season(season)
    if not 1 <= gameweek <= 38:
        raise HTTPException(status_code=400, detail="Gameweek must be between 1 and 38")
    try:
        return repository.journal_gameweek(season, gameweek)
    except SnapshotNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"No {season} GW{gameweek} journal entry") from error
    except ArtifactIntegrityError as error:
        raise HTTPException(status_code=409, detail={"code": "journal_integrity_failure", "message": str(error)}) from error


@app.get("/v1/journal/{season}/export")
def journal_export(season: str, filename: str = Query(default="gameweeks.csv")) -> FileResponse:
    season = _journal_season(season)
    if filename not in {"gameweeks.csv", "players.csv", "manifest.json", "README.md"}:
        raise HTTPException(status_code=400, detail="Unsupported journal export")
    try:
        path = repository.journal_export_path(season, filename)
    except SnapshotNotFoundError as error:
        raise HTTPException(status_code=404, detail="Journal export is not available") from error
    media_type = "text/csv" if filename.endswith(".csv") else "text/markdown" if filename.endswith(".md") else "application/json"
    return FileResponse(path, media_type=media_type, filename=f"fpl-journal-{season}-{filename}")


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
        meta=_meta(snapshot, model_version=MODEL_VERSION, feature_version="competitive-features-v4"), league_id=league_id, gameweek=gw, team_id=settings.my_team_id,
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


def _meta(snapshot: dict, model_version: str | None = None, feature_version: str | None = None) -> ApiMeta:
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
        data_version=str(snapshot.get("run_id") or raw_snapshot_at or "") or None,
        data_hash=snapshot.get("content_sha256") or snapshot.get("_artifact_sha256"), cutoff_at=snapshot_at,
        feature_version=feature_version, model_version=model_version,
        code_revision=settings.git_revision,
    )


@app.get("/v1/optimizer/transfers")
def transfer_optimizer(
    league_id: int = Query(default=settings.default_league_id, gt=0),
    gw: int | None = Query(default=None, ge=1, le=38),
    horizon: int = Query(default=5, ge=2, le=6),
    max_transfers: int = Query(default=2, ge=1, le=3),
    free_transfers: int = Query(default=1, ge=0, le=5),
    chip: str | None = Query(default=None, max_length=20),
) -> dict:
    gw = gw or _current_gameweek()
    snapshot = _league_or_404(league_id, gw)
    manager = next((row for row in snapshot.get("competitors", []) if row.get("entry_id") == settings.my_team_id), None)
    if manager is None:
        raise HTTPException(status_code=404, detail="Configured team is not present in this snapshot")
    bootstrap = repository.bootstrap()
    first_target = min(gw + 1, 38)
    targets = list(range(first_target, min(38, first_target + horizon - 1) + 1))
    horizon_rows = [build_projections(bootstrap, repository.fixtures(target)) for target in targets]
    first_rows = horizon_rows[0]
    players = {row.element: row for row in first_rows}
    horizon_maps = [{row.element: row for row in rows} for rows in horizon_rows]
    prices = {int(row["id"]): float(row.get("now_cost") or 0) / 10 for row in bootstrap.get("elements", [])}
    weights = tuple(round(0.85 ** index, 4) for index in range(len(targets)))
    if chip and chip.lower() not in {"wildcard", "freehit", "bboost", "3xc"}:
        raise HTTPException(status_code=400, detail="Unsupported chip mode")
    active_chip = chip or manager.get("active_chip")
    result = optimize_multiweek_transfers(
        [pick.get("element") for pick in manager.get("squad", [])], players, prices, horizon_maps,
        MultiWeekContext(
            bank=float(manager.get("gw_bank") or 0) / 10, free_transfers=free_transfers,
            weights=weights, max_transfers=max_transfers, active_chip=active_chip,
        ),
    )
    return {
        "meta": _bootstrap_meta(
            bootstrap, source="net-ev-optimizer", model_version=OPTIMIZER_VERSION,
            feature_version="v5-horizon-projections-1",
        ).model_dump(mode="json"),
        "league_id": league_id, "gameweek": gw, "target_gameweeks": targets,
        "free_transfers": free_transfers,
        "free_transfers_source": "request_or_default_assumption",
        "execution_authority": "telegram", "writes_enabled": False,
        **result,
    }


@app.get("/v1/leagues/{league_id}/live")
def league_live(league_id: int) -> dict:
    """Return official in-progress standings for the current gameweek.

    Squads are retained from the latest finalized snapshot when available;
    points, totals and league ranks come from the live FPL standings feed.
    """
    current = live_fpl.current_gameweek()
    live = live_fpl.league_standings(league_id)
    previous: dict[str, dict] = {}
    # Use the newest published snapshot as the squad/ownership fallback. This
    # also handles an API season rollover where FPL temporarily reports GW1.
    for prior_gw in range(current, 0, -1):
        try:
            previous = {str(row.get("entry_id")): row for row in repository.league(league_id, prior_gw).get("competitors", [])}
            if previous:
                break
        except SnapshotNotFoundError:
            continue
    managers = []
    for row in live["managers"]:
        old = previous.get(str(row.get("entry")), {})
        managers.append({
            **old,
            "entry_id": int(row.get("entry") or 0),
            "entry_name": row.get("entry_name") or old.get("entry_name", ""),
            "player_name": row.get("player_name") or old.get("player_name", ""),
            "gw_points": int(row.get("event_total") or 0),
            "total_points": int(row.get("total") or 0),
            "league_rank": int(row.get("rank") or 0),
            "overall_rank": int(old.get("overall_rank") or row.get("rank") or 0),
            "squad": old.get("squad", []),
            "squad_cost": float(old.get("squad_cost") or 0),
            "captain": old.get("captain", ""),
            "transfers_made": int(old.get("transfers_made") or 0),
        })
    return {"meta": {"source": "official-fpl-live", "snapshot_gameweek": current, "quality_status": "unknown", "generated_at": live["fetched_at"]}, "league_id": league_id, "gameweek": current, "count": len(managers), "declared_count": len(managers), "hydration_percent": 100.0, "managers": managers, "provisional": True}


@app.get("/v1/catalog/compact")
def compact_catalog() -> dict:
    bootstrap = repository.bootstrap()
    player_fields = ("id", "photo", "team", "event_points", "web_name", "element_type", "now_cost")
    team_fields = ("id", "name", "short_name", "code")
    event_fields = ("id", "name", "is_current", "is_next", "finished", "data_checked", "deadline_time")
    return {
        "meta": _bootstrap_meta(bootstrap).model_dump(mode="json"),
        "players": [{key: row.get(key) for key in player_fields} for row in bootstrap.get("elements", [])],
        "teams": [{key: row.get(key) for key in team_fields} for row in bootstrap.get("teams", [])],
        "events": [{key: row.get(key) for key in event_fields} for row in bootstrap.get("events", [])],
    }


def _bootstrap_meta(
    bootstrap: dict,
    source: str = "official-fpl-cache",
    model_version: str | None = None,
    feature_version: str | None = None,
) -> ApiMeta:
    raw = bootstrap.get("_meta") if isinstance(bootstrap.get("_meta"), dict) else {}
    snapshot_at = None
    if raw.get("fetched_at"):
        try:
            snapshot_at = datetime.fromisoformat(str(raw["fetched_at"]).replace("Z", "+00:00"))
        except ValueError:
            snapshot_at = None
    freshness = None if snapshot_at is None else round(
        (datetime.now(timezone.utc) - snapshot_at).total_seconds() / 3600, 2
    )
    issues = [] if snapshot_at is not None and raw.get("content_sha256") else ["bootstrap_provenance_missing"]
    return ApiMeta(
        source=source, snapshot_at=snapshot_at, freshness_hours=freshness,
        stale=freshness is None or freshness > 24,
        quality_status="valid" if not issues else "unknown", quality_issues=issues,
        data_version=str(raw.get("fetched_at") or "") or None,
        data_hash=raw.get("content_sha256"), cutoff_at=snapshot_at,
        feature_version=feature_version, model_version=model_version,
        code_revision=settings.git_revision,
    )


def _readiness() -> dict:
    checks: dict[str, dict[str, str | bool | int | float | None]] = {}
    try:
        bootstrap = repository.bootstrap()
        meta = _bootstrap_meta(bootstrap)
        checks["catalog"] = {
            "ok": meta.quality_status == "valid", "players": len(bootstrap.get("elements", [])),
            "snapshot_at": meta.snapshot_at.isoformat() if meta.snapshot_at else None,
            "freshness_hours": meta.freshness_hours,
        }
        fixture_horizon = repository.fixture_horizon(1, 38)
        populated = sum(1 for rows in fixture_horizon.values() if rows)
        checks["fixtures"] = {"ok": populated == 38, "populated_gameweeks": populated}
    except Exception as error:
        checks["catalog"] = {"ok": False, "error": type(error).__name__}
        checks["fixtures"] = {"ok": False, "error": type(error).__name__}
    try:
        index = repository.journal_index("2026-27")
        checks["journal"] = {"ok": True, "archived_gameweeks": len(index.get("gameweeks", []))}
    except Exception as error:
        checks["journal"] = {"ok": False, "error": type(error).__name__}
    ready_state = all(bool(check.get("ok")) for check in checks.values())
    return {
        "ready": ready_state, "revision": settings.git_revision,
        "checked_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
    }


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
        candidate = int(current["id"])
    else:
        next_event = next((event for event in events if event.get("is_next")), None)
        if next_event:
            candidate = max(1, int(next_event["id"]) - 1)
        else:
            finished = [int(event["id"]) for event in events if event.get("finished")]
            candidate = max(finished, default=1)
    for gameweek in range(candidate, 0, -1):
        try:
            snapshot = repository.league(settings.default_league_id, gameweek)
        except SnapshotNotFoundError:
            continue
        if snapshot_quality(snapshot)[0] != "valid":
            continue
        try:
            managers = snapshot.get("competitors", [])
            if managers:
                for manager in managers:
                    Manager.model_validate(manager)
                return gameweek
        except ValidationError:
            continue
    return max(1, candidate)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiMeta(BaseModel):
    run_id: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    snapshot_at: datetime | None = None
    source: str = "snapshot"
    stale: bool = False
    freshness_hours: float | None = None
    snapshot_gameweek: int | None = None
    quality_status: Literal["valid", "invalid", "unknown"] = "unknown"
    quality_issues: list[str] = Field(default_factory=list)


class Pick(BaseModel):
    model_config = ConfigDict(extra="ignore")

    element: int
    name: str
    position: Literal["GKP", "DEF", "MID", "FWD"]
    team: str
    cost: float
    multiplier: int
    is_captain: bool
    is_vice_captain: bool
    selected_by: float | None = None


class Manager(BaseModel):
    model_config = ConfigDict(extra="allow")

    entry_id: int
    entry_name: str
    player_name: str
    gw_points: int
    total_points: int
    overall_rank: int
    league_rank: int
    squad_cost: float
    captain: str
    transfers_made: int
    squad: list[Pick]


class TeamResponse(BaseModel):
    meta: ApiMeta
    league_id: int
    gameweek: int
    manager: Manager
    fixtures: list[dict[str, Any]]


class LeagueResponse(BaseModel):
    meta: ApiMeta
    league_id: int
    gameweek: int
    count: int
    declared_count: int
    hydration_percent: float
    managers: list[Manager]


class CatalogResponse(BaseModel):
    meta: ApiMeta
    players: list[dict[str, Any]]
    teams: list[dict[str, Any]]
    events: list[dict[str, Any]]


class EliteResponse(BaseModel):
    meta: ApiMeta
    league_id: int
    gameweek: int
    percentile: int
    count: int
    average_points: float
    managers: list[Manager]
    ownership: list[dict[str, Any]]
    captaincy: list[dict[str, Any]]


class RecommendationResponse(BaseModel):
    meta: ApiMeta
    league_id: int
    gameweek: int
    team_id: int
    elite_count: int
    elite_overlap: int
    elite_average_points: float
    transfers: list[dict[str, Any]]
    captains: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    missing_elite_players: list[dict[str, Any]]
    competitive: dict[str, Any]
    disclaimer: str


class IntegrationStatus(BaseModel):
    configured: bool
    mode: Literal["disconnected", "read_only", "approval"]
    bot_name: str | None
    approvals_enabled: bool
    missing: list[str]

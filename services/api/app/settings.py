from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    my_team_id: int
    default_league_id: int
    allowed_origins: tuple[str, ...]
    telegram_configured: bool
    telegram_bot_name: str | None
    autopilot_base_url: str | None
    autopilot_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        module_path = Path(__file__).resolve()
        default_data_dir = next(
            (parent / "data" for parent in module_path.parents if (parent / "data").is_dir()),
            module_path.parent / "data",
        )
        origins = os.getenv(
            "FPL_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        )
        return cls(
            data_dir=Path(os.getenv("FPL_DATA_DIR", default_data_dir)),
            my_team_id=int(os.getenv("FPL_MY_TEAM_ID", "2797967")),
            default_league_id=int(os.getenv("FPL_DEFAULT_LEAGUE_ID", "58005")),
            allowed_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
            telegram_configured=bool(os.getenv("TELEGRAM_WEBHOOK_SECRET") and os.getenv("TELEGRAM_ALLOWED_USER_IDS")),
            telegram_bot_name=os.getenv("TELEGRAM_BOT_NAME"),
            autopilot_base_url=os.getenv("FPL_AUTOPILOT_BASE_URL", "").rstrip("/") or None,
            autopilot_token=os.getenv("FPL_AUTOPILOT_TOKEN", "").strip() or None,
        )


settings = Settings.from_env()

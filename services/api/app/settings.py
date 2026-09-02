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
    snapshot_bucket: str | None
    git_revision: str | None
    build_time: str | None
    workspace_passcode: str | None
    owner_access_key: str | None
    owner_email: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    telegram_webhook_secret: str | None
    execution_webhook_url: str | None
    execution_webhook_token: str | None
    google_oauth_client_id: str | None

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
            snapshot_bucket=os.getenv("FPL_SNAPSHOT_BUCKET", "").strip() or None,
            git_revision=(os.getenv("FPL_GIT_SHA") or os.getenv("K_REVISION") or "").strip() or None,
            build_time=os.getenv("FPL_BUILD_TIME", "").strip() or None,
            workspace_passcode=os.getenv("FPL_WORKSPACE_PASSCODE", "").strip() or None,
            owner_access_key=os.getenv("FPL_OWNER_ACCESS_KEY", "").strip() or None,
            owner_email=os.getenv("FPL_OWNER_EMAIL", "").strip().casefold() or None,
            telegram_bot_token=os.getenv("FPL_TELEGRAM_BOT_TOKEN", "").strip() or None,
            telegram_chat_id=os.getenv("FPL_TELEGRAM_CHAT_ID", "").strip() or None,
            telegram_webhook_secret=os.getenv("FPL_TELEGRAM_WEBHOOK_SECRET", "").strip() or None,
            execution_webhook_url=os.getenv("FPL_EXECUTION_WEBHOOK_URL", "").strip() or None,
            execution_webhook_token=os.getenv("FPL_EXECUTION_WEBHOOK_TOKEN", "").strip() or None,
            google_oauth_client_id=os.getenv("FPL_GOOGLE_OAUTH_CLIENT_ID", "").strip() or None,
        )


settings = Settings.from_env()

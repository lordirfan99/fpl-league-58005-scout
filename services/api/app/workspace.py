"""Private, read-only-to-FPL planning workspace primitives.

This module intentionally persists only the owner's advisory draft.  It has
no FPL write client and no method that can submit a transfer, captain, lineup
or chip.  Firestore is used in production; an in-process store keeps local
development and tests deterministic until infrastructure is provisioned.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class WorkspaceLockedError(RuntimeError):
    pass


class WorkspaceStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, owner_id: str, target_gameweek: int) -> dict[str, Any] | None:
        with self._lock:
            value = self._items.get(f"{owner_id}:{target_gameweek}")
            return deepcopy(value) if value else None

    def save(self, owner_id: str, target_gameweek: int, payload: dict[str, Any], *, locked: bool = False) -> dict[str, Any]:
        key = f"{owner_id}:{target_gameweek}"
        with self._lock:
            existing = self._items.get(key)
            if existing and existing.get("locked"):
                raise WorkspaceLockedError("workspace_locked")
            now = datetime.now(timezone.utc).isoformat()
            record = {
                "schema_version": 1,
                "owner_id": owner_id,
                "target_gameweek": target_gameweek,
                "updated_at": now,
                "created_at": existing.get("created_at", now) if existing else now,
                "locked": locked,
                "draft": deepcopy(payload),
                "execution_authority": "manual_fpl",
                "writes_enabled": False,
            }
            self._items[key] = record
            return deepcopy(record)

    def lock(self, owner_id: str, target_gameweek: int) -> dict[str, Any] | None:
        with self._lock:
            key = f"{owner_id}:{target_gameweek}"
            record = self._items.get(key)
            if record is None:
                return None
            record["locked"] = True
            record["locked_at"] = datetime.now(timezone.utc).isoformat()
            return deepcopy(record)


workspace_store = WorkspaceStore()

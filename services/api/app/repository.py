from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from .journal import verify_record_hash

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - local development without GCS extras
    storage = None


class SnapshotNotFoundError(FileNotFoundError):
    pass


class ArtifactIntegrityError(RuntimeError):
    pass


class SnapshotRepository:
    """Read-only adapter around the existing collector output."""

    def __init__(self, data_dir: Path, bucket_name: str | None = None):
        self.data_dir = data_dir.resolve()
        self.bucket_name = bucket_name
        self._bucket = storage.Client().bucket(bucket_name) if bucket_name and storage else None
        self._remote_cache: dict[str, tuple[int | None, dict[str, Any]]] = {}

    def _path(self, filename: str) -> Path:
        path = (self.data_dir / filename).resolve()
        if self.data_dir not in path.parents:
            raise ValueError("Invalid snapshot path")
        if not path.is_file():
            raise SnapshotNotFoundError(filename)
        return path

    @lru_cache(maxsize=16)
    def _read_cached(self, filename: str, modified_ns: int) -> dict[str, Any]:
        del modified_ns
        with self._path(filename).open(encoding="utf-8") as source:
            return json.load(source)

    def _read_local(self, filename: str) -> dict[str, Any]:
        path = self._path(filename)
        return self._read_cached(filename, path.stat().st_mtime_ns)

    def _read_remote(self, filename: str) -> dict[str, Any] | None:
        if self._bucket is None:
            return None
        blob = self._bucket.blob(f"snapshots/{filename}")
        try:
            blob.reload()
            generation = int(blob.generation) if blob.generation else None
            cached = self._remote_cache.get(filename)
            if cached and cached[0] == generation:
                return cached[1]
            payload = json.loads(blob.download_as_text(encoding="utf-8"))
            self._remote_cache[filename] = (generation, payload)
            return payload
        except Exception:
            return None

    @staticmethod
    def _capture_timestamp(payload: dict[str, Any]) -> float | None:
        raw = payload.get("_meta", {}).get("fetched_at") or payload.get("fetched_at")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return None

    def _fresh_reference(self, filename: str) -> dict[str, Any]:
        """Choose the newest proven reference cache across image and GCS."""
        try:
            local = self._read_local(filename)
        except SnapshotNotFoundError:
            local = None
        remote = self._read_remote(filename)
        if local is None:
            if remote is None:
                raise SnapshotNotFoundError(filename)
            return remote
        if remote is None:
            return local
        local_time = self._capture_timestamp(local)
        remote_time = self._capture_timestamp(remote)
        if local_time is not None and (remote_time is None or local_time >= remote_time):
            return local
        if remote_time is not None:
            return remote
        # Preserve the historical remote-first behavior only when neither
        # candidate carries provenance.
        return remote

    def read(self, filename: str) -> dict[str, Any]:
        remote = self._read_remote(filename)
        if remote is not None:
            return remote
        # Packaged data remains a fail-soft recovery source if GCS is
        # temporarily unavailable or the requested artifact is not published.
        return self._read_local(filename)

    def league(self, league_id: int, gameweek: int) -> dict[str, Any]:
        return self.read(f"gw{gameweek}_league{league_id}_data.json")

    def bootstrap(self) -> dict[str, Any]:
        return self._fresh_reference("bootstrap_cache.json")

    def fixtures(self, gameweek: int) -> list[dict[str, Any]]:
        try:
            payload = self._fresh_reference("fixtures_cache.json")
            return payload.get("gameweeks", {}).get(str(gameweek), [])
        except SnapshotNotFoundError:
            pass
        try:
            payload = self.read(f"gw{gameweek}_fixtures.json")
        except SnapshotNotFoundError:
            return []
        return payload.get(f"gw{gameweek}", [])

    def fixture_horizon(self, from_gameweek: int, to_gameweek: int) -> dict[str, list[dict[str, Any]]]:
        return {str(gw): self.fixtures(gw) for gw in range(from_gameweek, to_gameweek + 1)}

    def journal_index(self, season: str) -> dict[str, Any]:
        payload = self.read(f"journal/{season}/index.json")
        for row in payload.get("gameweeks", []):
            gameweek = int(row.get("gameweek") or 0)
            entry = self.journal_gameweek(season, gameweek)
            if row.get("record_hash") != entry.get("record_hash"):
                raise ArtifactIntegrityError(f"Journal index hash mismatch for {season} GW{gameweek}")
        return payload

    def journal_gameweek(self, season: str, gameweek: int) -> dict[str, Any]:
        payload = self.read(f"journal/{season}/gw{gameweek:02d}.json")
        if not verify_record_hash(payload):
            raise ArtifactIntegrityError(f"Journal {season} GW{gameweek} failed hash verification")
        return payload

    def journal_export_path(self, season: str, filename: str) -> Path:
        return self._path(f"journal/{season}/exports/{filename}")

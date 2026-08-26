from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover - local development without GCS extras
    storage = None


class SnapshotNotFoundError(FileNotFoundError):
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

    def read(self, filename: str) -> dict[str, Any]:
        if self._bucket is not None:
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
                # Packaged data remains a fail-soft recovery source if GCS is
                # temporarily unavailable or the requested GW is not published.
                pass
        path = self._path(filename)
        return self._read_cached(filename, path.stat().st_mtime_ns)

    def league(self, league_id: int, gameweek: int) -> dict[str, Any]:
        return self.read(f"gw{gameweek}_league{league_id}_data.json")

    def bootstrap(self) -> dict[str, Any]:
        return self.read("bootstrap_cache.json")

    def fixtures(self, gameweek: int) -> list[dict[str, Any]]:
        try:
            payload = self.read("fixtures_cache.json")
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

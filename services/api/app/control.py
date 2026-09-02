"""Owner-only FPL action control primitives.

The public Scout API never receives FPL credentials.  This module records an
immutable approval trail and may hand an approved request to a separately
deployed private executor.  The executor is the sole component permitted to
hold an encrypted FPL browser session.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from threading import Lock
from typing import Any

import httpx


CHIPS = {"wildcard", "freehit", "bboost", "3xc"}


class ControlError(RuntimeError):
    pass


class ApprovalExpired(ControlError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ControlStore:
    """Thread-safe store with optional GCS durability and append-only events."""

    def __init__(self, bucket_name: str | None = None) -> None:
        self._actions: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._locked = False
        self._lock = Lock()
        self._bucket_name = bucket_name
        self._generations: dict[str, int] = {}
        self._state_loaded = False
        self._state_generation: int | None = None

    def configure_persistence(self, bucket_name: str | None) -> None:
        self._bucket_name = bucket_name

    def _bucket(self):
        if not self._bucket_name:
            return None
        from google.cloud import storage
        return storage.Client().bucket(self._bucket_name)

    @staticmethod
    def _action_name(action_id: str) -> str:
        return f"control/actions/{action_id}.json"

    def _persist(self, record: dict[str, Any]) -> None:
        bucket = self._bucket()
        if bucket is None:
            return
        action_id = record["action_id"]
        blob = bucket.blob(self._action_name(action_id))
        try:
            blob.upload_from_string(
                json.dumps(record, sort_keys=True, separators=(",", ":")).encode(), content_type="application/json",
                if_generation_match=self._generations.get(action_id, 0),
            )
        except Exception as error:
            self._actions.pop(action_id, None)
            self._generations.pop(action_id, None)
            raise ControlError("action_conflict") from error
        blob.reload()
        self._generations[action_id] = int(blob.generation)

    def _load(self, action_id: str) -> dict[str, Any] | None:
        cached = self._actions.get(action_id)
        if cached:
            return cached
        bucket = self._bucket()
        if bucket is None:
            return None
        blob = bucket.blob(self._action_name(action_id))
        if not blob.exists():
            return None
        value = json.loads(blob.download_as_text(encoding="utf-8"))
        self._actions[action_id] = value
        self._generations[action_id] = int(blob.generation)
        return value

    def _load_state(self) -> None:
        if self._state_loaded:
            return
        self._state_loaded = True
        bucket = self._bucket()
        if bucket is None:
            return
        blob = bucket.blob("control/state.json")
        if not blob.exists():
            return
        value = json.loads(blob.download_as_text(encoding="utf-8"))
        self._locked = bool(value.get("automation_locked"))
        self._state_generation = int(blob.generation)

    def _persist_state(self) -> None:
        bucket = self._bucket()
        if bucket is None:
            return
        blob = bucket.blob("control/state.json")
        try:
            blob.upload_from_string(
                json.dumps({"automation_locked": self._locked}, separators=(",", ":")).encode(), content_type="application/json",
                if_generation_match=self._state_generation or 0,
            )
        except Exception as error:
            self._state_loaded = False
            raise ControlError("automation_lock_conflict") from error
        blob.reload()
        self._state_generation = int(blob.generation)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._load_state()
            return {"automation_locked": self._locked, "actions": len(self._actions)}

    def set_lock(self, locked: bool, reason: str) -> dict[str, Any]:
        with self._lock:
            self._load_state()
            self._locked = locked
            self._persist_state()
            event = self._event("automation_locked" if locked else "automation_unlocked", {"reason": reason})
            self._events.append(event)
            self._write_event(event, "state")
            return {"automation_locked": self._locked, "event": deepcopy(event)}

    def create(self, payload: dict[str, Any], *, deadline: datetime, now: datetime | None = None) -> dict[str, Any]:
        current = now or _now()
        if deadline <= current:
            raise ControlError("deadline_passed")
        chip = str(payload.get("chip") or "").lower() or None
        if chip and chip not in CHIPS:
            raise ControlError("unsupported_chip")
        with self._lock:
            self._load_state()
            if self._locked:
                raise ControlError("automation_locked")
            action_id = secrets.token_urlsafe(18)
            expires = min(deadline, current + timedelta(minutes=15))
            request = deepcopy(payload)
            record = {
                "schema_version": 1, "action_id": action_id, "status": "pending_approval",
                "created_at": current.isoformat(), "expires_at": expires.isoformat(), "deadline": deadline.isoformat(),
                "request": request, "plan_hash": _hash(request), "chip": chip,
                "requires_chip_confirmation": bool(chip), "callback_token": secrets.token_urlsafe(18),
                "approval_count": 0, "audit": [],
            }
            self._append(record, "created", {"plan_hash": record["plan_hash"]})
            self._actions[action_id] = record
            self._persist(record)
            return deepcopy(record)

    def get(self, action_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._load(action_id)
            return deepcopy(record) if record else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            bucket = self._bucket()
            if bucket is not None:
                for blob in bucket.list_blobs(prefix="control/actions/"):
                    action_id = blob.name.rsplit("/", 1)[-1].removesuffix(".json")
                    self._load(action_id)
            rows = sorted(self._actions.values(), key=lambda row: row["created_at"], reverse=True)
            return deepcopy(rows[:limit])

    def approve(self, action_id: str, token: str, *, chip_confirmation: bool = False, now: datetime | None = None) -> dict[str, Any]:
        current = now or _now()
        with self._lock:
            record = self._load(action_id)
            if record is None:
                raise ControlError("action_not_found")
            if not secrets.compare_digest(record["callback_token"], token):
                raise ControlError("approval_token_invalid")
            if current >= datetime.fromisoformat(record["expires_at"]):
                record["status"] = "expired"
                self._append(record, "expired", {})
                self._persist(record)
                raise ApprovalExpired("approval_expired")
            if record["status"] in {"submitted", "succeeded", "failed", "cancelled"}:
                return deepcopy(record)
            if record["requires_chip_confirmation"] and not chip_confirmation:
                record["status"] = "pending_chip_confirmation"
                record["approval_count"] = 1
                self._append(record, "first_approval", {})
                self._persist(record)
                return deepcopy(record)
            if record["requires_chip_confirmation"] and record["status"] != "pending_chip_confirmation":
                raise ControlError("chip_first_confirmation_required")
            record["status"] = "approved"
            record["approval_count"] = 2 if record["requires_chip_confirmation"] else 1
            record["approved_at"] = current.isoformat()
            self._append(record, "approved", {"chip_confirmation": chip_confirmation})
            self._persist(record)
            return deepcopy(record)

    def mark_submission(self, action_id: str, *, result: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = self._load(action_id)
            if record is None:
                raise ControlError("action_not_found")
            if record["status"] == "succeeded":
                return deepcopy(record)
            if record["status"] != "approved":
                raise ControlError("action_not_approved")
            record["status"] = "succeeded" if result.get("ok") else "failed"
            record["submitted_at"] = _now().isoformat()
            record["execution_result"] = deepcopy(result)
            self._append(record, "submitted", {"ok": bool(result.get("ok"))})
            self._persist(record)
            return deepcopy(record)

    def _event(self, kind: str, details: dict[str, Any]) -> dict[str, Any]:
        return {"at": _now().isoformat(), "kind": kind, "details": details}

    def _append(self, record: dict[str, Any], kind: str, details: dict[str, Any]) -> None:
        event = self._event(kind, details)
        record["audit"].append(event)
        self._events.append({"action_id": record.get("action_id"), **event})
        self._write_event({"action_id": record.get("action_id"), **event}, kind)

    def _write_event(self, event: dict[str, Any], kind: str) -> None:
        bucket = self._bucket()
        if bucket is None:
            return
        event_id = secrets.token_urlsafe(12)
        blob = bucket.blob(f"control/audit/{event.get('action_id') or 'system'}/{event_id}-{kind}.json")
        blob.upload_from_string(json.dumps(event, sort_keys=True, separators=(",", ":")), content_type="application/json", if_generation_match=0)


class PrivateExecutor:
    """Calls an internal FPL session executor only after all approvals pass."""

    def __init__(self, url: str | None, token: str | None) -> None:
        self.url, self.token = url, token

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)

    def submit(self, record: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            return {"ok": False, "code": "executor_not_configured", "message": "Reconnect the private FPL session executor."}
        try:
            response = httpx.post(
                self.url or "", json={"action_id": record["action_id"], "plan_hash": record["plan_hash"], "request": record["request"]},
                headers={"x-fpl-executor-token": self.token or ""}, timeout=20,
            )
        except httpx.HTTPError:
            return {"ok": False, "code": "executor_unavailable"}
        if response.status_code >= 400:
            return {"ok": False, "code": "executor_rejected", "status_code": response.status_code}
        body = response.json()
        return {"ok": bool(body.get("ok")), "executor_reference": body.get("reference"), "code": body.get("code")}


class TelegramNotifier:
    """Outbound-only action cards; callback handling lives in the API webhook."""

    def __init__(self, token: str | None, chat_id: str | None) -> None:
        self.token, self.chat_id = token, chat_id

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_action(self, record: dict[str, Any], *, chip_confirmation: bool = False) -> bool:
        if not self.configured:
            return False
        action = "chip" if chip_confirmation else "approve"
        label = "Confirm chip use" if chip_confirmation else "Approve for 15 minutes"
        summary = str(record["request"].get("summary") or "FPL action")
        text = f"GW action: {summary}\nExpires: {record['expires_at']}\nPlan: {record['plan_hash'][:12]}"
        payload = {
            "chat_id": self.chat_id, "text": text,
            "reply_markup": {"inline_keyboard": [[{"text": label, "callback_data": f"fpl:{action}:{record['action_id']}:{record['callback_token']}"}]]},
        }
        try:
            response = httpx.post(f"https://api.telegram.org/bot{self.token}/sendMessage", json=payload, timeout=15)
            return response.is_success
        except httpx.HTTPError:
            return False


control_store = ControlStore()

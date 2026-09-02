from datetime import datetime, timedelta, timezone

import pytest

from app.control import ApprovalExpired, ControlError, ControlStore


def _request(chip: str | None = None) -> dict:
    return {"target_gameweek": 3, "changes": {"captain": 101}, "chip": chip}


def test_standard_action_requires_one_unexpired_approval() -> None:
    store = ControlStore()
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = store.create(_request(), deadline=now + timedelta(hours=2), now=now)
    approved = store.approve(action["action_id"], action["callback_token"], now=now + timedelta(minutes=1))
    assert approved["status"] == "approved"
    assert approved["approval_count"] == 1
    assert approved["plan_hash"]


def test_chip_requires_double_confirmation() -> None:
    store = ControlStore()
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = store.create(_request("wildcard"), deadline=now + timedelta(hours=2), now=now)
    first = store.approve(action["action_id"], action["callback_token"], now=now)
    assert first["status"] == "pending_chip_confirmation"
    complete = store.approve(action["action_id"], action["callback_token"], chip_confirmation=True, now=now)
    assert complete["status"] == "approved"
    assert complete["approval_count"] == 2


def test_expired_action_cannot_be_approved_or_submitted() -> None:
    store = ControlStore()
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = store.create(_request(), deadline=now + timedelta(hours=2), now=now)
    with pytest.raises(ApprovalExpired):
        store.approve(action["action_id"], action["callback_token"], now=now + timedelta(minutes=16))
    assert store.get(action["action_id"])["status"] == "expired"


def test_emergency_lock_blocks_new_actions() -> None:
    store = ControlStore()
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    store.set_lock(True, "test")
    with pytest.raises(ControlError, match="automation_locked"):
        store.create(_request(), deadline=now + timedelta(hours=2), now=now)

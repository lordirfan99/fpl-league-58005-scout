import pytest

from app.workspace import WorkspaceLockedError, WorkspaceStore


def test_owner_workspace_saves_read_only_draft_and_locks() -> None:
    store = WorkspaceStore()
    saved = store.save("owner", 3, {"active_chip": "wildcard", "squad": list(range(1, 16))})
    assert saved["writes_enabled"] is False
    assert saved["execution_authority"] == "manual_fpl"
    locked = store.lock("owner", 3)
    assert locked and locked["locked"] is True
    with pytest.raises(WorkspaceLockedError):
        store.save("owner", 3, {"squad": list(range(1, 16))})

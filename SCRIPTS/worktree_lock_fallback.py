"""Local fallback for worktree lock management when KIX/TRIX are unavailable."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LOCK_DIR = Path(".kiva/locks/worktrees")


def _ensure_lock_dir() -> None:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


def _lock_path(branch: str) -> Path:
    return LOCK_DIR / f"{branch}.lock"


def _is_lock_expired(lock_data: dict[str, Any]) -> bool:
    expires_at = datetime.fromisoformat(lock_data["expires_at"])
    return datetime.now(timezone.utc) >= expires_at


def acquire_lock(branch: str, agent_id: str, ttl: int = 3600) -> dict[str, Any]:
    """Acquire a local worktree lock."""
    _ensure_lock_dir()
    lock_path = _lock_path(branch)

    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
            if existing and not _is_lock_expired(existing):
                return {"status": "conflict", "lock_id": branch}
        except (json.JSONDecodeError, KeyError):
            pass

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl)
    lock_data = {
        "agent_id": agent_id,
        "acquired_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "owner_pid": os.getpid(),
    }
    lock_path.write_text(json.dumps(lock_data, indent=2) + "\n", encoding="utf-8")
    return {"status": "acquired", "lock_id": branch}


def release_lock(branch: str, agent_id: str) -> dict[str, Any]:
    """Release a local worktree lock."""
    lock_path = _lock_path(branch)
    if not lock_path.exists():
        return {"status": "released", "lock_id": branch}

    try:
        existing = json.loads(lock_path.read_text(encoding="utf-8"))
        if existing.get("agent_id") != agent_id:
            return {"status": "forbidden", "reason": "agent_id mismatch"}
    except (json.JSONDecodeError, KeyError):
        pass

    lock_path.unlink(missing_ok=True)
    return {"status": "released", "lock_id": branch}


def get_active_locks() -> dict[str, Any]:
    """Return all non-expired local locks."""
    if not LOCK_DIR.exists():
        return {"locks": []}

    active = []
    for lock_file in LOCK_DIR.glob("*.lock"):
        try:
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            if not _is_lock_expired(data):
                active.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    return {"locks": active}


def is_safe_to_purge(worktree_path: str) -> bool:
    """Best-effort check if a worktree can be purged."""
    path = Path(worktree_path)
    if not path.exists():
        return False

    locks = get_active_locks()
    for lock in locks.get("locks", []):
        if str(path) in str(lock):
            return False
    return True

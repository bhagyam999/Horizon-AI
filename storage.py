from __future__ import annotations

import os
import shutil
import sqlite3
import time
from pathlib import Path


def resolve_database_path(base_dir: str) -> str:
    """Resolve Horizon's persistent SQLite path.

    Priority:
      1. HORIZON_DB, when explicitly configured.
      2. /data/horizon.db on Railway/volume-based deployments.
      3. The project directory for normal local Windows/Linux runs.

    A Railway deployment is only persistent when /data is backed by a Railway
    Volume. The code cannot make an ephemeral container filesystem persistent.
    """
    configured = os.getenv("HORIZON_DB", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = Path(base_dir) / path
    else:
        railway = any(
            os.getenv(key, "").strip()
            for key in ("RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID")
        )
        data_dir = Path("/data")
        if railway and data_dir.exists() and data_dir.is_dir():
            path = data_dir / "horizon.db"
        else:
            path = Path(base_dir) / "horizon.db"

    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def migrate_legacy_database(target_path: str, legacy_path: str) -> bool:
    """Copy an existing old-location database into the persistent location once."""
    target = Path(target_path)
    legacy = Path(legacy_path)
    if target.resolve() == legacy.resolve():
        return False
    if target.exists() or not legacy.exists() or legacy.stat().st_size == 0:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, target)
    return True


def backup_database(db_path: str, keep: int = 7) -> str | None:
    """Create a consistent SQLite backup beside the database.

    Backups live in the same persistent directory so they survive a bot code
    redeploy when the directory is a mounted persistent volume.
    """
    source = Path(db_path)
    if not source.exists() or source.stat().st_size == 0:
        return None

    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    destination = backup_dir / f"horizon-{stamp}.db"

    src = sqlite3.connect(str(source), timeout=30)
    dst = sqlite3.connect(str(destination), timeout=30)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()

    backups = sorted(backup_dir.glob("horizon-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    return str(destination)

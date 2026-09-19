from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

log = logging.getLogger("horizon.storage")


def _usable_directory(path: Path) -> bool:
    """Return True when a directory exists (or can be created) and is writable."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".horizon_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def resolve_database_path(base_dir: str) -> str:
    """Resolve a database location without allowing storage config to crash startup.

    Priority:
      1. HORIZON_DB when its parent is usable.
      2. Railway's /data/horizon.db when /data is writable.
      3. The project directory for local/portable deployments.

    A Railway Volume mounted at /data is still required for persistence across
    container replacement. If /data is unavailable, Horizon deliberately falls
    back to the project directory so the Discord bot can still start.
    """
    base = Path(base_dir)
    configured = os.getenv("HORIZON_DB", "").strip()

    candidates: list[Path] = []
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = base / path
        candidates.append(path)
    else:
        railway = any(
            os.getenv(key, "").strip()
            for key in ("RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID")
        )
        data_dir = Path("/data")
        if railway:
            candidates.append(data_dir / "horizon.db")
        candidates.append(base / "horizon.db")

    # Always keep a local fallback last, even if an explicit persistent path was
    # configured incorrectly. This prevents a storage-path mistake from taking
    # the whole Discord bot offline.
    fallback = base / "horizon.db"
    if fallback not in candidates:
        candidates.append(fallback)

    for candidate in candidates:
        if _usable_directory(candidate.parent):
            if configured and candidate != fallback:
                log.info("Using configured database path: %s", candidate)
            elif candidate.parent == Path("/data"):
                log.info("Using Railway persistent database path: %s", candidate)
            else:
                log.info("Using local database path: %s", candidate)
            return str(candidate)

    # Extremely unusual fallback: create a temporary directory rather than
    # failing during bot construction. This is only a last-resort boot path.
    emergency = Path(tempfile.gettempdir()) / "horizon" / "horizon.db"
    emergency.parent.mkdir(parents=True, exist_ok=True)
    log.warning("No configured database directory is writable; using emergency path %s", emergency)
    return str(emergency)


def migrate_legacy_database(target_path: str, legacy_path: str) -> bool:
    """Copy an existing old-location database into the persistent location once."""
    target = Path(target_path)
    legacy = Path(legacy_path)
    try:
        if target.resolve() == legacy.resolve():
            return False
        if target.exists() or not legacy.exists() or legacy.stat().st_size == 0:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
        log.info("Migrated legacy database %s -> %s", legacy, target)
        return True
    except (OSError, PermissionError) as exc:
        # Migration failure should never prevent Discord from starting. The
        # schema initializer will create/use the selected database normally.
        log.warning("Could not migrate legacy database: %s", exc)
        return False


def backup_database(db_path: str, keep: int = 7) -> str | None:
    """Create a consistent SQLite backup beside the database.

    Backups live beside the database so they survive a bot code redeploy when
    the directory is backed by a persistent volume. Backup failures are raised
    to the caller, which decides whether they are fatal (they are not during
    startup or shutdown).
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

    backups = sorted(
        backup_dir.glob("horizon-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    return str(destination)

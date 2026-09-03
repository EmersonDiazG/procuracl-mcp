from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

from procura_cl.domain.errors import (
    DuplicateWatchlistError,
    RequestBudgetExceededError,
    WatchlistNotFoundError,
)
from procura_cl.domain.models import (
    ChangeKind,
    Opportunity,
    RequestBudgetStatus,
    SyncResult,
    Watchlist,
    WatchlistChange,
    WatchlistKind,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    kind TEXT NOT NULL,
    region TEXT,
    status TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist_terms (
    watchlist_id TEXT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (watchlist_id, term)
);

CREATE TABLE IF NOT EXISTS opportunity_snapshots (
    watchlist_id TEXT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    opportunity_code TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    last_change_kind TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, opportunity_code)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_changes
ON opportunity_snapshots(watchlist_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS sync_runs (
    id TEXT PRIMARY KEY,
    watchlist_id TEXT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    records_received INTEGER NOT NULL,
    records_new INTEGER NOT NULL,
    records_updated INTEGER NOT NULL,
    records_unchanged INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS api_request_usage (
    usage_date TEXT PRIMARY KEY,
    requests_used INTEGER NOT NULL CHECK (requests_used >= 0)
);

CREATE TABLE IF NOT EXISTS response_cache (
    cache_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _fingerprint(opportunity: Opportunity) -> tuple[str, str]:
    data = opportunity.model_dump(mode="json", exclude={"retrieved_at"})
    canonical = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest(), opportunity.model_dump_json()


class SQLiteRepository:
    """Small transactional repository for a single-user local MCP server."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def create_watchlist(self, watchlist: Watchlist) -> Watchlist:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO watchlists(id, name, kind, region, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        watchlist.id,
                        watchlist.name,
                        watchlist.kind.value,
                        watchlist.region,
                        watchlist.status,
                        watchlist.created_at.isoformat(),
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO watchlist_terms(watchlist_id, term, position)
                    VALUES (?, ?, ?)
                    """,
                    [(watchlist.id, term, index) for index, term in enumerate(watchlist.terms)],
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateWatchlistError(
                f"A watchlist named {watchlist.name!r} already exists"
            ) from error
        return watchlist

    def list_watchlists(self) -> list[Watchlist]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM watchlists ORDER BY created_at DESC"
            ).fetchall()
            return [self._watchlist(connection, row) for row in rows]

    def get_watchlist(self, watchlist_id: str) -> Watchlist:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM watchlists WHERE id = ?", (watchlist_id,)
            ).fetchone()
            if row is None:
                raise WatchlistNotFoundError(f"Watchlist {watchlist_id!r} was not found")
            return self._watchlist(connection, row)

    @staticmethod
    def _watchlist(connection: sqlite3.Connection, row: sqlite3.Row) -> Watchlist:
        terms = connection.execute(
            """
            SELECT term FROM watchlist_terms
            WHERE watchlist_id = ? ORDER BY position
            """,
            (row["id"],),
        ).fetchall()
        return Watchlist(
            id=row["id"],
            name=row["name"],
            terms=[term["term"] for term in terms],
            kind=WatchlistKind(row["kind"]),
            region=row["region"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def delete_watchlist(self, watchlist_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
            return cursor.rowcount > 0

    def save_snapshot(self, watchlist_id: str, opportunity: Opportunity) -> ChangeKind:
        fingerprint, payload = _fingerprint(opportunity)
        now = _now().isoformat()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT fingerprint FROM opportunity_snapshots
                WHERE watchlist_id = ? AND opportunity_code = ?
                """,
                (watchlist_id, opportunity.code),
            ).fetchone()
            if row is None:
                change = ChangeKind.NEW
                connection.execute(
                    """
                    INSERT INTO opportunity_snapshots(
                        watchlist_id, opportunity_code, fingerprint, payload_json,
                        first_seen_at, last_seen_at, changed_at, last_change_kind
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        watchlist_id,
                        opportunity.code,
                        fingerprint,
                        payload,
                        now,
                        now,
                        now,
                        change.value,
                    ),
                )
                return change
            if row["fingerprint"] == fingerprint:
                connection.execute(
                    """
                    UPDATE opportunity_snapshots SET last_seen_at = ?
                    WHERE watchlist_id = ? AND opportunity_code = ?
                    """,
                    (now, watchlist_id, opportunity.code),
                )
                return ChangeKind.UNCHANGED
            change = ChangeKind.UPDATED
            connection.execute(
                """
                UPDATE opportunity_snapshots
                SET fingerprint = ?, payload_json = ?, last_seen_at = ?,
                    changed_at = ?, last_change_kind = ?
                WHERE watchlist_id = ? AND opportunity_code = ?
                """,
                (
                    fingerprint,
                    payload,
                    now,
                    now,
                    change.value,
                    watchlist_id,
                    opportunity.code,
                ),
            )
            return change

    def list_changes(
        self, watchlist_id: str, *, since: datetime | None, limit: int
    ) -> list[WatchlistChange]:
        self.get_watchlist(watchlist_id)
        parameters: list[str | int] = [watchlist_id]
        since_clause = ""
        if since is not None:
            since_clause = "AND changed_at >= ?"
            parameters.append(since.isoformat())
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json, last_change_kind, changed_at
                FROM opportunity_snapshots
                WHERE watchlist_id = ? {since_clause}
                ORDER BY changed_at DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [
            WatchlistChange(
                watchlist_id=watchlist_id,
                change=ChangeKind(row["last_change_kind"]),
                opportunity=Opportunity.model_validate_json(row["payload_json"]),
                changed_at=datetime.fromisoformat(row["changed_at"]),
            )
            for row in rows
        ]

    def save_sync_result(self, result: SyncResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sync_runs(
                    id, watchlist_id, status, records_received, records_new,
                    records_updated, records_unchanged, started_at, finished_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.sync_id,
                    result.watchlist_id,
                    result.status.value,
                    result.records_received,
                    result.records_new,
                    result.records_updated,
                    result.records_unchanged,
                    result.started_at.isoformat(),
                    result.finished_at.isoformat(),
                    result.error,
                ),
            )

    def consume_request(self, *, daily_limit: int) -> RequestBudgetStatus:
        today = date.today()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT requests_used FROM api_request_usage WHERE usage_date = ?",
                (today.isoformat(),),
            ).fetchone()
            used = int(row["requests_used"]) if row else 0
            if used >= daily_limit:
                raise RequestBudgetExceededError(
                    f"Daily upstream request budget of {daily_limit} has been exhausted"
                )
            used += 1
            connection.execute(
                """
                INSERT INTO api_request_usage(usage_date, requests_used) VALUES (?, ?)
                ON CONFLICT(usage_date) DO UPDATE SET requests_used = excluded.requests_used
                """,
                (today.isoformat(), used),
            )
        return RequestBudgetStatus(
            date=today,
            used=used,
            limit=daily_limit,
            remaining=daily_limit - used,
        )

    def get_request_budget(self, *, daily_limit: int) -> RequestBudgetStatus:
        today = date.today()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT requests_used FROM api_request_usage WHERE usage_date = ?",
                (today.isoformat(),),
            ).fetchone()
        used = int(row["requests_used"]) if row else 0
        return RequestBudgetStatus(
            date=today,
            used=used,
            limit=daily_limit,
            remaining=max(0, daily_limit - used),
        )

    def get_cache(self, key: str) -> str | None:
        now = _now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, expires_at FROM response_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            if datetime.fromisoformat(row["expires_at"]) <= now:
                connection.execute("DELETE FROM response_cache WHERE cache_key = ?", (key,))
                return None
            return str(row["payload_json"])

    def set_cache(self, key: str, payload: str, *, ttl_seconds: int) -> None:
        expires_at = _now().timestamp() + ttl_seconds
        expiration = datetime.fromtimestamp(expires_at, tz=UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO response_cache(cache_key, payload_json, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    expires_at = excluded.expires_at
                """,
                (key, payload, expiration),
            )

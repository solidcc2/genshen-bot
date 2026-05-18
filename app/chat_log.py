from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class ChatLogEntry:
    chat_id: str
    user_id: str
    text: str
    timestamp: datetime
    scene: str = ""
    platform: str = ""
    message_id: str = ""


class ChatLogStore:
    def __init__(self, db_path: str, max_count: int = 0, min_count: int = 0) -> None:
        self._db_path = db_path
        self._max_count = max_count
        self._min_count = min_count
        self._conn: aiosqlite.Connection | None = None

    async def _init(self) -> aiosqlite.Connection:
        if self._conn is not None:
            return self._conn

        parent = Path(self._db_path).parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        # Schema check: recreate if timestamp column type is wrong (pre-v2)
        cursor = await self._conn.execute("PRAGMA table_info(chat_log)")
        columns = {row[1]: row[2] for row in await cursor.fetchall()}
        if columns.get("timestamp") != "INTEGER":
            await self._conn.execute("DROP TABLE IF EXISTS chat_log")
            await self._conn.execute(
                """CREATE TABLE chat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    message_id TEXT NOT NULL DEFAULT '',
                    timestamp INTEGER NOT NULL,
                    scene TEXT NOT NULL DEFAULT '',
                    platform TEXT NOT NULL DEFAULT ''
                )"""
            )

        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_log_lookup ON chat_log(chat_id, timestamp DESC)"
        )
        await self._conn.commit()
        return self._conn

    async def record(self, entry: ChatLogEntry) -> None:
        conn = await self._init()
        await conn.execute(
            "INSERT INTO chat_log (chat_id, user_id, text, message_id, timestamp, scene, platform) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (entry.chat_id, entry.user_id, entry.text, entry.message_id, int(entry.timestamp.timestamp() * 1000), entry.scene, entry.platform),
        )
        await conn.commit()
        if self._max_count > 0:
            await self._trim_if_needed(entry.chat_id)

    async def get_recent(self, chat_id: str, limit: int = 30, cursor_msg_id: str | None = None) -> list[ChatLogEntry]:
        conn = await self._init()
        if cursor_msg_id:
            rows = await conn.execute_fetchall(
                """SELECT chat_id, user_id, text, message_id, timestamp, scene, platform
                   FROM chat_log WHERE chat_id = ? AND id > (
                       SELECT COALESCE(MAX(id), 0) FROM chat_log WHERE chat_id = ? AND message_id = ?
                   ) ORDER BY timestamp DESC LIMIT ?""",
                (chat_id, chat_id, cursor_msg_id, limit),
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT chat_id, user_id, text, message_id, timestamp, scene, platform FROM chat_log WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
                (chat_id, limit),
            )
        return [
            ChatLogEntry(
                chat_id=row[0],
                user_id=row[1],
                text=row[2],
                message_id=row[3],
                timestamp=datetime.fromtimestamp(row[4] / 1000, tz=timezone.utc),
                scene=row[5],
                platform=row[6],
            )
            for row in rows
        ]

    async def count(self, chat_id: str) -> int:
        conn = await self._init()
        rows = await conn.execute_fetchall(
            "SELECT COUNT(*) FROM chat_log WHERE chat_id = ?",
            (chat_id,),
        )
        return rows[0][0] if rows else 0

    async def trim(self, chat_id: str, keep: int) -> None:
        """Keep only the latest `keep` entries for chat_id, delete older ones."""
        conn = await self._init()
        await conn.execute(
            "DELETE FROM chat_log WHERE chat_id = ? AND id NOT IN (SELECT id FROM chat_log WHERE chat_id = ? ORDER BY id DESC LIMIT ?)",
            (chat_id, chat_id, keep),
        )
        await conn.commit()

    async def clear(self, chat_id: str) -> None:
        conn = await self._init()
        await conn.execute("DELETE FROM chat_log WHERE chat_id = ?", (chat_id,))
        await conn.commit()

    async def _trim_if_needed(self, chat_id: str) -> None:
        count = await self.count(chat_id)
        if count > self._max_count:
            await self.trim(chat_id, self._min_count)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

import aiosqlite
from datetime import datetime, date
from typing import Any


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS work_days (
                    day TEXT PRIMARY KEY,
                    is_closed INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS time_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day TEXT NOT NULL,
                    time TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(day, time),
                    FOREIGN KEY(day) REFERENCES work_days(day) ON DELETE CASCADE
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    user_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    day TEXT NOT NULL,
                    time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    booking_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    run_at TEXT NOT NULL,
                    FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
                )
                """
            )
            await db.commit()

    async def add_work_day(self, day: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO work_days(day, is_closed) VALUES(?, 0)",
                (day,),
            )
            await db.commit()

    async def close_day(self, day: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE work_days SET is_closed = 1 WHERE day = ?", (day,))
            await db.commit()

    async def add_time_slot(self, day: str, time: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO work_days(day, is_closed) VALUES(?, 0)", (day,)
            )
            await db.execute(
                "INSERT OR IGNORE INTO time_slots(day, time, is_deleted) VALUES(?, ?, 0)",
                (day, time),
            )
            await db.execute(
                "UPDATE time_slots SET is_deleted = 0 WHERE day = ? AND time = ?",
                (day, time),
            )
            await db.commit()

    async def delete_time_slot(self, day: str, time: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE time_slots SET is_deleted = 1 WHERE day = ? AND time = ?",
                (day, time),
            )
            await db.commit()

    async def get_work_days_for_month(self, year: int, month: int) -> list[str]:
        prefix = f"{year:04d}-{month:02d}-"
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT day FROM work_days WHERE day LIKE ? AND is_closed = 0 ORDER BY day",
                (f"{prefix}%",),
            )
            rows = await cursor.fetchall()
        return [r[0] for r in rows]

    async def get_available_slots(self, day: str) -> list[str]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT ts.time
                FROM time_slots ts
                JOIN work_days wd ON wd.day = ts.day
                WHERE ts.day = ?
                  AND ts.is_deleted = 0
                  AND wd.is_closed = 0
                  AND NOT EXISTS (
                    SELECT 1 FROM bookings b
                    WHERE b.day = ts.day AND b.time = ts.time AND b.status = 'active'
                  )
                ORDER BY ts.time
                """,
                (day,),
            )
            rows = await cursor.fetchall()
        return [r[0] for r in rows]

    async def user_has_active_booking(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM bookings WHERE user_id = ? AND status = 'active' LIMIT 1",
                (user_id,),
            )
            row = await cursor.fetchone()
        return bool(row)

    async def create_booking(
        self, user_id: int, user_name: str, phone: str, day: str, time: str
    ) -> int:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO bookings(user_id, user_name, phone, day, time, created_at, status)
                VALUES(?, ?, ?, ?, ?, ?, 'active')
                """,
                (user_id, user_name, phone, day, time, now),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_booking(self, user_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, user_name, phone, day, time
                FROM bookings
                WHERE user_id = ? AND status = 'active'
                LIMIT 1
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "phone": row[3],
            "day": row[4],
            "time": row[5],
        }


    async def get_booking_by_id(self, booking_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, user_id, user_name, phone, day, time, status FROM bookings WHERE id = ?",
                (booking_id,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "user_name": row[2],
            "phone": row[3],
            "day": row[4],
            "time": row[5],
            "status": row[6],
        }

    async def cancel_booking(self, booking_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
            await db.execute("DELETE FROM reminders WHERE booking_id = ?", (booking_id,))
            await db.commit()

    async def cancel_booking_by_user(self, user_id: int) -> dict[str, Any] | None:
        booking = await self.get_user_booking(user_id)
        if not booking:
            return None
        await self.cancel_booking(booking["id"])
        return booking

    async def get_schedule_for_day(self, day: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT ts.time, b.user_name, b.phone, b.user_id
                FROM time_slots ts
                LEFT JOIN bookings b
                  ON b.day = ts.day AND b.time = ts.time AND b.status = 'active'
                WHERE ts.day = ? AND ts.is_deleted = 0
                ORDER BY ts.time
                """,
                (day,),
            )
            rows = await cursor.fetchall()
        return [
            {
                "time": r[0],
                "user_name": r[1],
                "phone": r[2],
                "user_id": r[3],
            }
            for r in rows
        ]

    async def get_bookings_for_day(self, day: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT id, user_id, user_name, phone, time
                FROM bookings
                WHERE day = ? AND status = 'active'
                ORDER BY time
                """,
                (day,),
            )
            rows = await cursor.fetchall()
        return [
            {"id": r[0], "user_id": r[1], "user_name": r[2], "phone": r[3], "time": r[4]}
            for r in rows
        ]

    async def save_reminder(self, booking_id: int, user_id: int, run_at: datetime) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO reminders(booking_id, user_id, run_at) VALUES(?, ?, ?)",
                (booking_id, user_id, run_at.isoformat()),
            )
            await db.commit()

    async def delete_reminder(self, booking_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM reminders WHERE booking_id = ?", (booking_id,))
            await db.commit()

    async def get_pending_reminders(self) -> list[dict[str, Any]]:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                SELECT r.booking_id, r.user_id, r.run_at, b.day, b.time
                FROM reminders r
                JOIN bookings b ON b.id = r.booking_id
                WHERE b.status = 'active' AND r.run_at > ?
                """,
                (now,),
            )
            rows = await cursor.fetchall()
        return [
            {
                "booking_id": r[0],
                "user_id": r[1],
                "run_at": r[2],
                "day": r[3],
                "time": r[4],
            }
            for r in rows
        ]

    async def get_days_next_month(self) -> list[str]:
        today = date.today()
        days = []
        for i in range(32):
            d = today.fromordinal(today.toordinal() + i)
            if d.month != today.month and i > 0:
                break
            days.append(d.isoformat())
        return days

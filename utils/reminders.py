from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from database.db import Database


class ReminderService:
    def __init__(self, scheduler: AsyncIOScheduler, bot: Bot, db: Database):
        self.scheduler = scheduler
        self.bot = bot
        self.db = db

    async def schedule_for_booking(
        self, booking_id: int, user_id: int, day: str, time: str
    ) -> None:
        visit_dt = datetime.fromisoformat(f"{day}T{time}:00")
        run_at = visit_dt - timedelta(hours=24)
        if run_at <= datetime.now():
            return

        job_id = f"reminder_{booking_id}"
        self.scheduler.add_job(
            self._send_reminder,
            "date",
            id=job_id,
            run_date=run_at,
            kwargs={"booking_id": booking_id, "user_id": user_id, "time": time},
            replace_existing=True,
        )
        await self.db.save_reminder(booking_id, user_id, run_at)

    async def cancel_for_booking(self, booking_id: int) -> None:
        job_id = f"reminder_{booking_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        await self.db.delete_reminder(booking_id)

    async def restore_jobs(self) -> None:
        reminders = await self.db.get_pending_reminders()
        for item in reminders:
            run_at = datetime.fromisoformat(item["run_at"])
            self.scheduler.add_job(
                self._send_reminder,
                "date",
                id=f"reminder_{item['booking_id']}",
                run_date=run_at,
                kwargs={
                    "booking_id": item["booking_id"],
                    "user_id": item["user_id"],
                    "time": item["time"],
                },
                replace_existing=True,
            )

    async def _send_reminder(self, booking_id: int, user_id: int, time: str) -> None:
        await self.bot.send_message(
            user_id,
            (
                "<b>Напоминаем, что вы записаны на наращивание ресниц завтра "
                f"в {time}.\nЖдём вас ️</b>"
            ),
            parse_mode="HTML",
        )
        await self.db.delete_reminder(booking_id)

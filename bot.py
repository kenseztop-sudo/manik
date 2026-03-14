import asyncio
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import load_config
from database.db import Database
from handlers import user, admin
from utils.middlewares import ServicesMiddleware
from utils.reminders import ReminderService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    load_dotenv()
    config = load_config()
    if not config.bot_token:
        raise RuntimeError("Set BOT_TOKEN in environment")

    db = Database(config.database_path)
    await db.init()

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    scheduler = AsyncIOScheduler()
    scheduler.start()

    reminders = ReminderService(scheduler=scheduler, bot=bot, db=db)
    await reminders.restore_jobs()

    services_middleware = ServicesMiddleware(
        db=db,
        config=config,
        reminders=reminders,
    )

    dp.update.middleware(services_middleware)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

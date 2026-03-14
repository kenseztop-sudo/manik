from dataclasses import dataclass
import os


@dataclass
class Config:
    bot_token: str
    admin_id: int
    schedule_channel_id: int
    database_path: str = "manicure_bot.db"


def load_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_id=int(os.getenv("ADMIN_ID", "0")),
        schedule_channel_id=int(os.getenv("SCHEDULE_CHANNEL_ID", "0")),
        database_path=os.getenv("DATABASE_PATH", "manicure_bot.db"),
    )

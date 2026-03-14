import calendar
from datetime import date, datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗓 Записаться", callback_data="book:start")
    builder.button(text="❌ Отменить запись", callback_data="book:cancel")
    builder.button(text="💅 Прайсы", callback_data="info:prices")
    builder.button(text="📸 Портфолио", callback_data="info:portfolio")
    builder.adjust(1)
    return builder.as_markup()


def calendar_kb(year: int, month: int, available_days: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal:prev:{year}:{month}"),
        InlineKeyboardButton(text=f"{calendar.month_name[month]} {year}", callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal:next:{year}:{month}"),
    )

    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="noop") for d in week_days])

    month_calendar = calendar.monthcalendar(year, month)
    available_set = set(available_days)

    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
                continue
            day_str = date(year, month, day).isoformat()
            if day_str in available_set and date(year, month, day) >= date.today():
                row.append(
                    InlineKeyboardButton(text=str(day), callback_data=f"date:{day_str}")
                )
            else:
                row.append(InlineKeyboardButton(text=f"·{day}", callback_data="noop"))
        builder.row(*row)

    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return builder.as_markup()


def slots_kb(day: str, slots: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"slot:{day}:{slot}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="book:start"))
    return builder.as_markup()


def confirm_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no")],
        ]
    )


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить рабочий день", callback_data="admin:add_day")
    builder.button(text="🕐 Добавить слот", callback_data="admin:add_slot")
    builder.button(text="🗑 Удалить слот", callback_data="admin:delete_slot")
    builder.button(text="🔒 Закрыть день", callback_data="admin:close_day")
    builder.button(text="📋 Расписание на дату", callback_data="admin:schedule")
    builder.button(text="❌ Отменить запись клиента", callback_data="admin:cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


def admin_booking_list_kb(bookings: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in bookings:
        builder.button(
            text=f"{b['time']} — {b['user_name']}",
            callback_data=f"admin:cancel:{b['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def portfolio_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Смотреть портфолио",
                    url="https://ru.pinterest.com/crystalwithluv/_created/",
                )
            ]
        ]
    )


def month_shift(year: int, month: int, direction: int) -> tuple[int, int]:
    idx = (year * 12 + month - 1) + direction
    new_year = idx // 12
    new_month = idx % 12 + 1
    return new_year, new_month


def can_show_month(year: int, month: int) -> bool:
    now = datetime.now()
    max_idx = now.year * 12 + now.month
    target = year * 12 + month
    return target in {max_idx, max_idx + 1}

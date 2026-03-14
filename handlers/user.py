from datetime import date

from aiogram import F, Bot, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import Config
from database.db import Database
from keyboards.inline import (
    main_menu_kb,
    calendar_kb,
    slots_kb,
    confirm_booking_kb,
    portfolio_kb,
    month_shift,
    can_show_month,
)
from utils.reminders import ReminderService
from utils.states import BookingStates

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Добро пожаловать в бот записи на маникюр!</b>\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu")
async def open_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "<b>Главное меню</b>", parse_mode="HTML", reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "info:prices")
async def show_prices(callback: CallbackQuery):
    await callback.message.answer(
        "<b>Прайс:</b>\n\n"
        "• Френч — <b>1000₽</b>\n"
        "• Квадрат — <b>500₽</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "info:portfolio")
async def show_portfolio(callback: CallbackQuery):
    await callback.message.answer(
        "<b>Портфолио работ:</b>", parse_mode="HTML", reply_markup=portfolio_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "book:start")
async def start_booking(
    callback: CallbackQuery, state: FSMContext, db: Database
):
    if await db.user_has_active_booking(callback.from_user.id):
        await callback.message.answer("У вас уже есть активная запись. Сначала отмените её.")
        await callback.answer()
        return

    today = date.today()
    days = await db.get_work_days_for_month(today.year, today.month)
    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        "<b>Выберите дату:</b>",
        parse_mode="HTML",
        reply_markup=calendar_kb(today.year, today.month, days),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_date, F.data.startswith("cal:"))
async def flip_calendar(callback: CallbackQuery, db: Database):
    _, direction, y, m = callback.data.split(":")
    year, month = month_shift(int(y), int(m), -1 if direction == "prev" else 1)
    if not can_show_month(year, month):
        await callback.answer("Можно смотреть только текущий и следующий месяц", show_alert=True)
        return

    days = await db.get_work_days_for_month(year, month)
    await callback.message.edit_reply_markup(reply_markup=calendar_kb(year, month, days))
    await callback.answer()


@router.callback_query(BookingStates.choosing_date, F.data.startswith("date:"))
async def pick_date(callback: CallbackQuery, state: FSMContext, db: Database):
    chosen_day = callback.data.split(":", 1)[1]
    slots = await db.get_available_slots(chosen_day)
    if not slots:
        await callback.answer("На этот день нет свободного времени", show_alert=True)
        return

    await state.update_data(day=chosen_day)
    await state.set_state(BookingStates.choosing_time)
    await callback.message.edit_text(
        f"<b>Дата:</b> {chosen_day}\n<b>Выберите время:</b>",
        parse_mode="HTML",
        reply_markup=slots_kb(chosen_day, slots),
    )
    await callback.answer()


@router.callback_query(BookingStates.choosing_time, F.data.startswith("slot:"))
async def pick_time(callback: CallbackQuery, state: FSMContext):
    _, day, time = callback.data.split(":")
    await state.update_data(day=day, time=time)
    await state.set_state(BookingStates.entering_name)
    await callback.message.answer("Введите ваше имя:")
    await callback.answer()


@router.message(BookingStates.entering_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(BookingStates.entering_phone)
    await message.answer("Введите номер телефона:")


@router.message(BookingStates.entering_phone)
async def get_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    await state.set_state(BookingStates.confirming)
    await message.answer(
        "<b>Проверьте запись:</b>\n"
        f"Дата: <b>{data['day']}</b>\n"
        f"Время: <b>{data['time']}</b>\n"
        f"Имя: <b>{data['name']}</b>\n"
        f"Телефон: <b>{data['phone']}</b>",
        parse_mode="HTML",
        reply_markup=confirm_booking_kb(),
    )


@router.callback_query(BookingStates.confirming, F.data == "confirm:no")
async def cancel_confirm(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Запись отменена.", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "confirm:yes")
async def save_booking(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    config: Config,
    bot: Bot,
    reminders: ReminderService,
):
    user_id = callback.from_user.id
    if await db.user_has_active_booking(user_id):
        await state.clear()
        await callback.message.answer("У вас уже есть активная запись.", reply_markup=main_menu_kb())
        await callback.answer()
        return

    data = await state.get_data()
    slots = await db.get_available_slots(data["day"])
    if data["time"] not in slots:
        await state.clear()
        await callback.message.answer("Слот уже занят, выберите другое время.", reply_markup=main_menu_kb())
        await callback.answer()
        return

    booking_id = await db.create_booking(
        user_id=user_id,
        user_name=data["name"],
        phone=data["phone"],
        day=data["day"],
        time=data["time"],
    )
    await reminders.schedule_for_booking(booking_id, user_id, data["day"], data["time"])

    text = (
        "<b>Новая запись:</b>\n"
        f"Клиент: <b>{data['name']}</b>\n"
        f"Телефон: <b>{data['phone']}</b>\n"
        f"Дата: <b>{data['day']}</b>\n"
        f"Время: <b>{data['time']}</b>\n"
        f"User ID: <code>{user_id}</code>"
    )
    await bot.send_message(config.admin_id, text, parse_mode="HTML")
    if config.schedule_channel_id:
        await bot.send_message(config.schedule_channel_id, text, parse_mode="HTML")

    await state.clear()
    await callback.message.answer(
        "✅ Запись успешно создана!", reply_markup=main_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "book:cancel")
async def cancel_user_booking(
    callback: CallbackQuery, db: Database, reminders: ReminderService
):
    booking = await db.cancel_booking_by_user(callback.from_user.id)
    if not booking:
        await callback.message.answer("У вас нет активной записи.")
        await callback.answer()
        return

    await reminders.cancel_for_booking(booking["id"])
    await callback.message.answer(
        f"❌ Ваша запись на {booking['day']} {booking['time']} отменена.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()

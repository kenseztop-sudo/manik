from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import Config
from database.db import Database
from keyboards.inline import admin_menu_kb, admin_booking_list_kb
from utils.reminders import ReminderService
from utils.states import AdminStates

router = Router()


def admin_only(user_id: int, config: Config) -> bool:
    return user_id == config.admin_id


@router.message(Command("admin"))
async def admin_panel(message: Message, config: Config, state: FSMContext):
    if not admin_only(message.from_user.id, config):
        await message.answer("Недостаточно прав")
        return
    await state.clear()
    await message.answer("<b>Админ-панель</b>", parse_mode="HTML", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admin:"))
async def admin_callbacks_router(callback: CallbackQuery, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)


@router.callback_query(F.data == "admin:add_day")
async def admin_add_day(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.adding_day)
    await callback.message.answer("Введите дату рабочего дня в формате YYYY-MM-DD")
    await callback.answer()


@router.message(AdminStates.adding_day)
async def admin_add_day_input(message: Message, state: FSMContext, db: Database):
    await db.add_work_day(message.text.strip())
    await state.clear()
    await message.answer("День добавлен.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:add_slot")
async def admin_add_slot_start(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.adding_slot_day)
    await callback.message.answer("Введите дату для слота YYYY-MM-DD")
    await callback.answer()


@router.message(AdminStates.adding_slot_day)
async def admin_add_slot_day(message: Message, state: FSMContext):
    await state.update_data(day=message.text.strip())
    await state.set_state(AdminStates.adding_slot_time)
    await message.answer("Введите время слота HH:MM")


@router.message(AdminStates.adding_slot_time)
async def admin_add_slot_time(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    await db.add_time_slot(data["day"], message.text.strip())
    await state.clear()
    await message.answer("Слот добавлен.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:delete_slot")
async def admin_delete_slot_start(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.deleting_slot_day)
    await callback.message.answer("Введите дату слота YYYY-MM-DD")
    await callback.answer()


@router.message(AdminStates.deleting_slot_day)
async def admin_delete_slot_day(message: Message, state: FSMContext):
    await state.update_data(day=message.text.strip())
    await state.set_state(AdminStates.deleting_slot_time)
    await message.answer("Введите время слота HH:MM")


@router.message(AdminStates.deleting_slot_time)
async def admin_delete_slot_time(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    await db.delete_time_slot(data["day"], message.text.strip())
    await state.clear()
    await message.answer("Слот удалён.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:close_day")
async def admin_close_day_start(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.closing_day)
    await callback.message.answer("Введите дату для закрытия YYYY-MM-DD")
    await callback.answer()


@router.message(AdminStates.closing_day)
async def admin_close_day_input(message: Message, state: FSMContext, db: Database):
    await db.close_day(message.text.strip())
    await state.clear()
    await message.answer("День закрыт.", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:schedule")
async def admin_schedule_start(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.schedule_day)
    await callback.message.answer("Введите дату расписания YYYY-MM-DD")
    await callback.answer()


@router.message(AdminStates.schedule_day)
async def admin_schedule_input(message: Message, state: FSMContext, db: Database):
    day = message.text.strip()
    rows = await db.get_schedule_for_day(day)
    if not rows:
        text = "Слотов на этот день нет."
    else:
        lines = [f"<b>Расписание на {day}</b>"]
        for row in rows:
            if row["user_name"]:
                lines.append(
                    f"• {row['time']} — {row['user_name']} ({row['phone']}) [ID: {row['user_id']}]"
                )
            else:
                lines.append(f"• {row['time']} — свободно")
        text = "\n".join(lines)
    await state.clear()
    await message.answer(text, parse_mode="HTML", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:cancel_booking")
async def admin_cancel_booking_start(callback: CallbackQuery, state: FSMContext, config: Config):
    if not admin_only(callback.from_user.id, config):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AdminStates.cancel_booking_day)
    await callback.message.answer("Введите дату YYYY-MM-DD, чтобы выбрать запись для отмены")
    await callback.answer()


@router.message(AdminStates.cancel_booking_day)
async def admin_cancel_booking_day(
    message: Message, state: FSMContext, db: Database
):
    day = message.text.strip()
    bookings = await db.get_bookings_for_day(day)
    if not bookings:
        await state.clear()
        await message.answer("На эту дату нет активных записей.", reply_markup=admin_menu_kb())
        return
    await state.set_state(AdminStates.cancel_booking_select)
    await message.answer(
        f"Выберите запись для отмены ({day}):",
        reply_markup=admin_booking_list_kb(bookings),
    )


@router.callback_query(AdminStates.cancel_booking_select, F.data.startswith("admin:cancel:"))
async def admin_cancel_booking_select(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    reminders: ReminderService,
    bot,
):
    booking_id = int(callback.data.split(":")[-1])
    booking = await db.get_booking_by_id(booking_id)
    await db.cancel_booking(booking_id)
    await reminders.cancel_for_booking(booking_id)
    if booking:
        await bot.send_message(booking["user_id"], f"❌ Ваша запись на {booking['day']} {booking['time']} отменена администратором.")
    await state.clear()
    await callback.message.answer("Запись отменена администратором.", reply_markup=admin_menu_kb())
    await callback.answer("Готово")

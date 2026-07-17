import asyncio
import datetime
import httpx
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, BotCommand, BotCommandScopeAllPrivateChats
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from states import BookingStates
from keyboards import (
    branches_keyboard, instructor_card_keyboard, days_keyboard,
    time_keyboard, main_menu_keyboard, bookings_menu_keyboard
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

router = Router()


async def api(method: str, path: str, **kwargs):
    async with httpx.AsyncClient() as client:
        response = await getattr(client, method)(f"{API_URL}{path}", **kwargs)
        return response.json()


async def build_main_menu_text(student_id: int) -> str:
    data = await api("get", f"/students/{student_id}/status")

    slot = data.get("active_slot")
    if slot:
        if slot["status"] == "confirmed":
            booking_line = f"📅 Запись на урок: {slot['date']} в {slot['time']} ✅"
            waiting_line = "⏳ Статус записи: подтверждено"
        else:
            booking_line = f"📅 Запись на урок: {slot['date']} в {slot['time']}"
            waiting_line = "⏳ Статус записи: ожидание подтверждения"
    else:
        booking_line = "📅 Запись на урок: отсутсвует"
        waiting_line = "⏳ Статус записи: запись отсутсвует"

    remaining = data["total_lessons"] - data["used_lessons"]
    return (
        f"👤 {data['full_name']}\n\n"
        f"{booking_line}\n"
        f"{waiting_line}\n\n"
        f"🎓 Всего уроков: {data['total_lessons']}\n"
        f"📊 Остаток неиспользованных уроков: {remaining}\n\n"
        f"Выберите действие:"
    )


async def get_student_id(state: FSMContext) -> int:
    data = await state.get_data()
    return data["student_id"]


# ──────────────────────────────────────────────
# СТАРТ → ВВОД КЛЮЧА
# ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_for_key)
    await message.answer(
        'Вас приветствует Бот автошколы "Техника"!\n'
        "Для дальнейшей работы введите идентификационный ключ"
    )


@router.message(BookingStates.waiting_for_key)
async def process_key(message: Message, state: FSMContext):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/students/identify", json={
                "key": message.text.strip(),
                "telegram_id": str(message.from_user.id)
            })
            student = response.json()
            print(f"DEBUG identify response: {student}")  
    except Exception:
        await message.answer("Ошибка соединения с сервером. Попробуйте позже.")
        return

    if "detail" in student:
        if response.status_code == 409:
            # Этот Telegram уже привязан к другому ученику — направляем к администратору
            await message.answer(
                "⚠️ Этот Telegram уже привязан к другому ученику.\n"
                "Обратитесь к администратору автошколы — он отвяжет старый аккаунт "
                "в панели управления, после чего вы сможете привязаться заново."
            )
        else:
            await message.answer("Ключ не найден. Проверьте правильность ввода и попробуйте снова.")
        return

    await state.update_data(student_id=student["id"])
    await state.set_state(BookingStates.main_menu)
    await message.answer(await build_main_menu_text(student["id"]), reply_markup=main_menu_keyboard())


# ──────────────────────────────────────────────
# МЕНЮ КОМАНД
# ──────────────────────────────────────────────
@router.message(Command("menu"))
async def cmd_menu(message: Message ,state: FSMContext):
    result = await api("get", f"/students/by-telegram/{message.from_user.id}")

    if "detail" in result:
        await state.set_state(BookingStates.waiting_for_key)
        await message.answer("Введите ключ идентификации")
        return
    

    await state.update_data(student_id=result["id"])
    await state.set_state(BookingStates.main_menu)
    await message.answer(await build_main_menu_text(result["id"]), reply_markup=main_menu_keyboard())

# ──────────────────────────────────────────────
# ОКНО ЗАПИСЕЙ
# ──────────────────────────────────────────────
async def build_my_bookings_menu(student_id: int) -> tuple[str, list]:
    data = await api("get", f"/students/{student_id}/bookings")

    if not data or isinstance(data, dict):
        return "У вас пока нет записей.\nДобавьте новую — она сразу появится в этом окне.", []

    lines = ["📋 Мои записи:\n\n" "🛑 ВАЖНО! Если вы отменяете запись позденее чем за 24 часа до его проведения это занятие списывается с вашего баланса 🛑\n"]
    slot_ids = []
    for i, booking in enumerate(data, start=1):
        status = "✅ Статус заявки: Подтверждено" if booking["status"] == "confirmed" else "⏳ Статус заявки: Ожидание подтверждения"
        lines.append(
            f"{i}. {booking['date']} в {booking['time'][:5]}\n"
            f" 👨‍🏫 Инструктор: {booking['instructor']}\n"
            f" 🚗 Машина: {booking['car_model']}\n"
            f" 🕹️ КПП: {booking['kpp']}\n"
            f" {status}\n"
        )
        slot_ids.append(booking["slot_id"])

    return "\n".join(lines), slot_ids

@router.callback_query(BookingStates.main_menu, F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery, state: FSMContext):
    student_id = await get_student_id(state)
    await state.set_state(BookingStates.bookings_menu)

    text, slot_ids = await build_my_bookings_menu(student_id)
    await callback.message.answer(text, reply_markup=bookings_menu_keyboard(slot_ids))
    await callback.answer()

# ──────────────────────────────────────────────
# ОТМЕНА КОНКРЕТНОЙ ЗАПИСИ
# ──────────────────────────────────────────────
@router.callback_query(BookingStates.bookings_menu, F.data.startswith("cancel_slot_"))
async def cancel_specific_slot(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[2])
    student_id = await get_student_id(state)

    result = await api("post", f"/slots/cancel_by_id/{slot_id}")

    if "detail" in result:
        await callback.answer("Не удалось отменить запись", show_alert=True)
        return

    text, slot_ids = await build_my_bookings_menu(student_id)
    await callback.message.edit_text(text, reply_markup=bookings_menu_keyboard(slot_ids))
    await callback.answer("Запись отменена ✓")


# ──────────────────────────────────────────────
# ГЛАВНОЕ МЕНЮ
# ──────────────────────────────────────────────
@router.callback_query(F.data == "start_booking")
async def start_booking(callback: CallbackQuery, state: FSMContext):

    branches = await api("get", "/branches/")
    
    await state.set_state(BookingStates.choosing_branch)
    await callback.message.answer(
        "Запись на практическое занятие:\nВыберите филиал где бы вы хотели пройти практическое занятие",
        reply_markup=branches_keyboard(branches)
    )
    await callback.answer()


# ──────────────────────────────────────────────
# КНОПКА "ОТМЕНА" — работает с ЛЮБОГО шага
# ──────────────────────────────────────────────
@router.callback_query(F.data == "cancel_to_menu")
async def cancel_to_menu(callback: CallbackQuery, state: FSMContext):
    student_id = await get_student_id(state)
    await state.set_state(BookingStates.main_menu)
    await callback.message.answer(await build_main_menu_text(student_id), reply_markup=main_menu_keyboard())
    await callback.answer()


# ──────────────────────────────────────────────
# ВЫБОР ФИЛИАЛА → КАРУСЕЛЬ ИНСТРУКТОРОВ
# ──────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_branch, F.data.startswith("branch_"))
async def show_branch_instructors(callback: CallbackQuery, state: FSMContext):
    branch_id = int(callback.data.split("_")[1])
    instructors = await api("get", f"/instructors/branch/{branch_id}")

    if isinstance(instructors, dict) and "detail" in instructors:
        await callback.message.answer("В этом филиале пока нет инструкторов.")
        await callback.answer()
        return

    instructor_ids = [i["id"] for i in instructors]
    await state.update_data(instructor_ids=instructor_ids, current_index=0, branch_id=branch_id)
    await state.set_state(BookingStates.viewing_instructor)
    await send_instructor_card(callback.message, instructors[0], 0, len(instructors), as_new=True)
    await callback.answer()


async def send_instructor_card(message: Message, instructor: dict, index: int, total: int, as_new: bool):
    caption = (
        f"<b>{instructor['full_name']}</b>\n"
        f"Водительский стаж с {instructor['driving_since']}г.\n"
        f"Стаж инструктора с {instructor['instructor_since']}г.\n"
        f"Машина: {instructor['car_model']} ({instructor['transmission_type']})"
    )
    keyboard = instructor_card_keyboard(instructor["id"], index, total)
    has_photo = os.path.exists(instructor["photo_path"])

    if as_new:
        if has_photo:
            await message.answer_photo(photo=FSInputFile(instructor["photo_path"]),
                                       caption=caption, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
        return

    if has_photo:
        media = InputMediaPhoto(media=FSInputFile(instructor["photo_path"]), caption=caption, parse_mode="HTML")
        await message.edit_media(media=media, reply_markup=keyboard)
    else:
        await message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(BookingStates.viewing_instructor, F.data.in_(["next_instructor", "prev_instructor"]))
async def navigate_instructors(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ids = data["instructor_ids"]
    index = data["current_index"]
    index += 1 if callback.data == "next_instructor" else -1
    index = max(0, min(index, len(ids) - 1))
    await state.update_data(current_index=index)

    instructor = await api("get", f"/instructors/{ids[index]}")
    await send_instructor_card(callback.message, instructor, index, len(ids), as_new=False)
    await callback.answer()


@router.callback_query(BookingStates.viewing_instructor, F.data == "back_to_branches")
async def back_to_branches(callback: CallbackQuery, state: FSMContext):
    branches = await api("get", "/branches/")
    
    await state.set_state(BookingStates.choosing_branch)
    await callback.message.answer("Выберите филиал:", reply_markup=branches_keyboard(branches))
    await callback.answer()


# ──────────────────────────────────────────────
# ВЫБОР ИНСТРУКТОРА → ВЫБОР ДНЯ
# ──────────────────────────────────────────────
@router.callback_query(BookingStates.viewing_instructor, F.data.startswith("select_instructor_"))
async def select_instructor(callback: CallbackQuery, state: FSMContext):
    instructor_id = int(callback.data.split("_")[2])
    await state.update_data(selected_instructor_id=instructor_id, week_offset=0)
    await state.set_state(BookingStates.choosing_day)
    await show_days(callback.message, instructor_id, week_offset=0, as_new=True)
    await callback.answer()


async def show_days(message: Message, instructor_id: int, week_offset: int, as_new: bool):
    instructor = await api("get", f"/instructors/{instructor_id}")
    today = datetime.date.today()
    week_start = today + datetime.timedelta(weeks=week_offset)
    week_end = week_start + datetime.timedelta(days=6)

    free_slots = await api("get", f"/slots/week/{instructor_id}",
                           params={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()})

    available_days = sorted(set(s["date"] for s in free_slots))
    available_days = [datetime.date.fromisoformat(d) for d in available_days]

    text = (
        f"Инструктор: {instructor['full_name']}\n"
        f"Выберите желаемый день\n"
        f"Неделя: с {week_start.strftime('%d.%m')} по {week_end.strftime('%d.%m')}"
    )
    keyboard = days_keyboard(available_days, instructor["max_weeks_ahead"], week_offset)

    if as_new:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.edit_text(text, reply_markup=keyboard)


@router.callback_query(BookingStates.choosing_day, F.data.in_(["next_week", "prev_week"]))
async def navigate_weeks(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offset = data.get("week_offset", 0)
    offset += 1 if callback.data == "next_week" else -1
    await state.update_data(week_offset=offset)
    await show_days(callback.message, data["selected_instructor_id"], offset, as_new=False)
    await callback.answer()


# ──────────────────────────────────────────────
# ВЫБОР ДНЯ → ВЫБОР ВРЕМЕНИ
# ──────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_day, F.data.startswith("day_"))
async def choose_day(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    chosen_date = datetime.date.fromisoformat(date_str)
    await state.update_data(chosen_date=date_str)
    await state.set_state(BookingStates.choosing_time)

    data = await state.get_data()
    instructor = await api("get", f"/instructors/{data['selected_instructor_id']}")
    free_slots = await api("get", f"/slots/free/{data['selected_instructor_id']}",
                           params={"date": date_str})

    text = f"Инструктор: {instructor['full_name']}\nДень: {chosen_date.strftime('%d.%m, %A')}\nВыберите время"
    await callback.message.edit_text(text, reply_markup=time_keyboard(free_slots))
    await callback.answer()


@router.callback_query(BookingStates.choosing_time, F.data == "back_to_days")
async def back_to_days(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(BookingStates.choosing_day)
    await show_days(callback.message, data["selected_instructor_id"], data.get("week_offset", 0), as_new=False)
    await callback.answer()


@router.callback_query(BookingStates.choosing_day, F.data == "back_to_instructor")
async def back_to_instructor(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ids = data["instructor_ids"]
    index = data["current_index"]
    instructor = await api("get", f"/instructors/{ids[index]}")
    await state.set_state(BookingStates.viewing_instructor)
    await send_instructor_card(callback.message, instructor, index, len(ids), as_new=False)
    await callback.answer()


# ──────────────────────────────────────────────
# ВЫБОР ВРЕМЕНИ → ПОДТВЕРЖДЕНИЕ
# ──────────────────────────────────────────────
@router.callback_query(BookingStates.choosing_time, F.data.startswith("slot_"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[1])
    data = await state.get_data()

    result = await api("post", "/slots/book", json={
        "slot_id": slot_id,
        "student_id": data["student_id"]
    })

    error_detail = result.get("detail")
    if error_detail == "Слот уже занят":
        await callback.answer("Этот слот уже заняли, выберите другое время", show_alert=True)
        return
    
    elif error_detail == "Достигнут лимит записей (3)":
        await callback.answer("Достигнут лимит записей (3шт)", show_alert=True)
        return

    slot = await api("get", f"/slots/{slot_id}")
    instructor = await api("get", f"/instructors/{slot['instructor_id']}")

    text = (
        "Ваша запись оформлена!\n"
        f"Инструктор: {instructor['full_name']}\n"
        f"День: {slot['date']}\n"
        f"Время: {slot['time']}\n"
        "Как только инструктор подтвердит вашу запись мы вам это сообщим.\n"
        "Спасибо что пользуетесь нашим сервисом!"
    )

    await callback.message.answer(text)
    await state.set_state(BookingStates.main_menu)
    await callback.message.answer(await build_main_menu_text(data["student_id"]), reply_markup=main_menu_keyboard())
    await callback.answer()



async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/menu", description="Главное меню"),
    ]
    
    await bot.set_my_commands(
        commands=main_menu_commands,
        scope=BotCommandScopeAllPrivateChats()
    )

# ──────────────────────────────────────────────
# ЗАПУСК
# ──────────────────────────────────────────────
async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await set_main_menu(bot)  
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
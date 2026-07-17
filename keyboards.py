from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

CANCEL_BUTTON = InlineKeyboardButton(text="↩️ Вернуться на главную", callback_data="cancel_to_menu")

def branches_keyboard(branches):
    rows = [[InlineKeyboardButton(text=b["name"], callback_data=f"branch_{b['id']}")] for b in branches]
    rows.append([CANCEL_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def instructor_card_keyboard(instructor_id: int, index: int, total: int):
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_instructor"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="Далее ➡️", callback_data="next_instructor"))
    rows = [[InlineKeyboardButton(text="Выбрать этого инструктора", callback_data=f"select_instructor_{instructor_id}")]]
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="🏢 К списку филиалов", callback_data="back_to_branches")])
    rows.append([CANCEL_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def days_keyboard(available_days: list, max_weeks_ahead: int, week_offset: int):
    rows = [[InlineKeyboardButton(text=d.strftime("%d.%m (%a)"), callback_data=f"day_{d.isoformat()}")] for d in available_days]
    nav = []
    if week_offset > 0:
        nav.append(InlineKeyboardButton(text="⏮️ Пред. неделя", callback_data="prev_week"))
    if week_offset < max_weeks_ahead - 1:
        nav.append(InlineKeyboardButton(text="След. неделя ⏭️", callback_data="next_week"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⏪ Назад", callback_data="back_to_instructor")])
    rows.append([CANCEL_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def time_keyboard(free_slots: list):
    rows = [[InlineKeyboardButton(
        text=s["time"][:5],
        callback_data=f"slot_{s['id']}"
    )] for s in free_slots]
    rows.append([InlineKeyboardButton(text="⏪ Назад", callback_data="back_to_days")])
    rows.append([CANCEL_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗓️ Запись на практические занятия", callback_data="start_booking")],
        [InlineKeyboardButton(text="📄 Мои записи", callback_data="my_bookings")]
    ])

def bookings_menu_keyboard(slot_ids: list):
    rows = []
    for i, slot_id in enumerate(slot_ids, start=1):
        rows.append([InlineKeyboardButton(
            text=f"🗑️ Отменить запись {i}",
            callback_data=f"cancel_slot_{slot_id}"
        )])
    rows.append([InlineKeyboardButton(text="📆 Добавить новую запись", callback_data="start_booking")])
    rows.append([InlineKeyboardButton(text="↩️ Вернуться на главную", callback_data="cancel_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
    
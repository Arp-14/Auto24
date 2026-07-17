from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_for_key = State()      # ввод идентификационного ключа
    main_menu = State()            # главное меню после идентификации
    bookings_menu = State()        # окно со всеми записями
    choosing_branch = State()      # выбор филиала
    viewing_instructor = State()   # карусель инструкторов
    choosing_day = State()         # выбор дня
    choosing_time = State()        # выбор времени

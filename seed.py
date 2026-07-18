import datetime
import random
from database import engine, SessionLocal, Base
from models import Instructor, Slot

db = SessionLocal()

try:
    instructors = db.query(Instructor).all()
    if not instructors:
        print("Инструкторы не найдены! Сначала добавь их через админку.")
        exit()

    print(f"Найдено инструкторов: {len(instructors)}")

    # Удаляем только свободные слоты (не трогаем уже забронированные)
    deleted = db.query(Slot).filter(Slot.is_booked == False).delete()
    db.commit()
    print(f"Удалено старых свободных слотов: {deleted}")

    all_times = [
        datetime.time(8, 0),
        datetime.time(10, 0),
        datetime.time(12, 0),
        datetime.time(14, 0),
        datetime.time(16, 0),
        datetime.time(18, 0),
        datetime.time(20, 0),
    ]

    today = datetime.date.today()
    slots_to_add = []

    for instructor in instructors:
        # 2 случайных выходных в неделю для каждого инструктора
        days_off = random.sample(range(7), 2)

        for week in range(instructor.max_weeks_ahead):
            for day_offset in range(7):
                absolute_day = week * 7 + day_offset
                day = today + datetime.timedelta(days=absolute_day)

                if day_offset in days_off:
                    continue  # выходной

                # от 4 до 6 окон в день
                count = random.randint(4, 6)
                chosen_times = sorted(random.sample(all_times, count))

                for t in chosen_times:
                    # не дублируем если слот уже есть (на случай повторного запуска)
                    exists = db.query(Slot).filter(
                        Slot.instructor_id == instructor.id,
                        Slot.date == day,
                        Slot.time == t
                    ).first()
                    if not exists:
                        slots_to_add.append(Slot(
                            instructor_id=instructor.id,
                            date=day,
                            time=t
                        ))

    db.add_all(slots_to_add)
    db.commit()
    print(f"Добавлено слотов: {len(slots_to_add)}")
    print("Готово!")

except Exception as e:
    db.rollback()
    print(f"Ошибка: {e}")
finally:
    db.close()
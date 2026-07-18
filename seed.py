import datetime
from database import engine, SessionLocal, Base
from models import Branch, Instructor, Slot, Student
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_INSTRUCTOR_PASSWORD = "instructor2024"

print("Удаление старых таблиц...")
Base.metadata.drop_all(bind=engine)

print("Создание таблиц в PostgreSQL...")
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    print("Очистка старых данных...")
    db.query(Slot).delete()
    db.query(Instructor).delete()
    db.query(Branch).delete()
    db.query(Student).delete()
    db.commit()

    print("Создание филиалов...")
    b1 = Branch(name="Бибирево")
    b2 = Branch(name="Тимирязевская")
    db.add_all([b1, b2])
    db.commit() 

    print("Создание инструкторов...")
    hashed_pw = pwd_context.hash(DEFAULT_INSTRUCTOR_PASSWORD)
    i1 = Instructor(branch_id=b2.id, full_name="Насиров Рамил", photo_path="photos/instructor1.jpg",
                     driving_since=2007, instructor_since=2014, car_model="Cheurolet Klan", transmission_type="механика",
                     password_hash=hashed_pw)
    i2 = Instructor(branch_id=b2.id, full_name="Паршин Николай", photo_path="photos/instructor2.jpg",
                     driving_since=1989, instructor_since=2020, car_model="Lada Vesta", transmission_type="автомат",
                     password_hash=hashed_pw)
    i3 = Instructor(branch_id=b2.id, full_name="Гусейнов Эмиль", photo_path="photos/instructor3.jpg",
                     driving_since=2005, instructor_since=2024, car_model="Renault Logan", transmission_type="механика",
                     password_hash=hashed_pw)
    i4 = Instructor(branch_id=b2.id, full_name="Михаил Туляков", photo_path="photos/instructor4.jpg",
                     driving_since=2011, instructor_since=2020, car_model="Kia Spectra", transmission_type="механика",
                     password_hash=hashed_pw)
    db.add_all([i1, i2, i3, i4])
    db.commit()

    print("Генерация слотов на 14 дней...")
    today = datetime.date.today()
    times = [datetime.time(8, 0), datetime.time(10, 0), datetime.time(12, 0), datetime.time(15, 0), datetime.time(17, 0)]

    slots_to_add = []
    for instructor in [i1, i2, i3, i4]:
        for day_offset in range(14):
            day = today + datetime.timedelta(days=day_offset)
            for t in times:
                slots_to_add.append(Slot(instructor_id=instructor.id, date=day, time=t))
    
    db.add_all(slots_to_add)
    db.commit()

    print("Создание тестового ученика...")
    test_key = "H455h@425J4502"
    student = Student(telegram_id=None, full_name="Владимир Вольфович", identification_key=test_key,
                       total_lessons=16, used_lessons=10)
    db.add(student)
    db.commit()

    print(f"База успешно заполнена. Тестовый ключ ученика: {test_key}")
    print(f"Пароль администратора: смотри ADMIN_PASSWORD в auth_simple.py")
    print(f"Пароль всех сид-инструкторов: {DEFAULT_INSTRUCTOR_PASSWORD} (ID инструкторов: 1-4)")

except Exception as e:
    db.rollback()
    print(f"Ошибка при заполнении базы: {e}")

finally:
    db.close()

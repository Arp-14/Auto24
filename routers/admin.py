from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Slot, Student, Instructor
from schemas import RejectBooking, UpdateDefaultMessage
from .auth_simple import create_session, require_admin, require_instructor, ADMIN_PASSWORD
import datetime as dt
import os
import httpx
import secrets

router = APIRouter(prefix="/admin", tags=["admin"])

BOT_TOKEN = os.getenv("BOT_TOKEN")

@router.post("/login")
def admin_login(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Неверный пароль")
    token = create_session("admin")
    return {"token": token, "role": "admin"}

async def notify_student(telegram_id: str, text: str):
    if not telegram_id or not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": telegram_id, "text": text})
    except Exception:
        pass


# Заявки инструктора (доступно только самому инструктору)
@router.get("/pending/{instructor_id}")
def get_pending(instructor_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slots = db.query(Slot).filter(
        Slot.instructor_id == instructor_id,
        Slot.status == "pending"
    ).order_by(Slot.date, Slot.time).all()

    result = []
    for slot in slots:
        student = db.query(Student).filter(Student.id == slot.booked_by_student_id).first()
        result.append({
            "id": slot.id,
            "date": slot.date.strftime("%d.%m.%Y"),
            "weekday": slot.date.strftime("%A"),
            "time": slot.time.strftime("%H:%M"),
            "student_name": student.full_name if student else "Неизвестно"
        })
    return result


@router.post("/slots/{slot_id}/complete")
def complete_lesson(slot_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    if slot.status != "confirmed":
        raise HTTPException(status_code=400, detail="Отметить можно только подтверждённое занятие")

    student = db.query(Student).filter(Student.id == slot.booked_by_student_id).first()
    if student:
        student.used_lessons += 1

    slot.status = "completed"
    db.commit()
    return {"message": "Занятие отмечено как пройденное"}


@router.post("/slots/{slot_id}/no-show")
def mark_no_show(slot_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")

    student = db.query(Student).filter(Student.id == slot.booked_by_student_id).first()
    if student:
        student.used_lessons += 1

    slot.status = "no_show"
    db.commit()
    return {"message": "Отмечено как неявка, занятие списано"}


@router.post("/confirm/{slot_id}")
async def confirm_slot(slot_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    slot.status = "confirmed"
    db.commit()

    if slot.booked_by_student_id:
        student = db.query(Student).filter(Student.id == slot.booked_by_student_id).first()
        if student and student.telegram_id:
            await notify_student(
                student.telegram_id,
                f"✅ Ваша запись на {slot.date.strftime('%d.%m.%Y')} в {slot.time.strftime('%H:%M')} подтверждена инструктором!"
            )
    return {"message": "Запись подтверждена"}


@router.post("/reject/{slot_id}")
async def reject_slot(slot_id: int, data: RejectBooking, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")

    instructor = db.query(Instructor).filter(Instructor.id == slot.instructor_id).first()
    message = data.message or instructor.default_reject_message
    student_id = slot.booked_by_student_id

    slot.is_booked = False
    slot.status = "free"
    slot.booked_by_student_id = None
    db.commit()

    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student and student.telegram_id:
            await notify_student(
                student.telegram_id,
                f"❌ Ваша запись на {slot.date.strftime('%d.%m.%Y')} в {slot.time.strftime('%H:%M')} отменена.\n{message}"
            )
    return {"message": "Запись отклонена", "sent_message": message}


@router.get("/instructor/{instructor_id}/default-message")
def get_default_message(instructor_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Инструктор не найден")
    return {"message": instructor.default_reject_message}


@router.put("/instructor/{instructor_id}/default-message")
def update_default_message(instructor_id: int, data: UpdateDefaultMessage, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Инструктор не найден")
    instructor.default_reject_message = data.message
    db.commit()
    return {"message": "Сообщение обновлено"}


@router.post("/slots/add")
def add_slot(instructor_id: int, date: dt.date, time: dt.time, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    existing = db.query(Slot).filter(
        Slot.instructor_id == instructor_id,
        Slot.date == date,
        Slot.time == time
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Слот уже существует")
    slot = Slot(instructor_id=instructor_id, date=date, time=time)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return {"id": slot.id, "date": str(slot.date), "time": str(slot.time)}


@router.delete("/slots/{slot_id}")
def delete_slot(slot_id: int, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Нельзя удалить занятый слот")
    db.delete(slot)
    db.commit()
    return {"message": "Слот удалён"}


@router.get("/slots/all/{instructor_id}")
def get_all_slots(instructor_id: int, week_start: dt.date, week_end: dt.date, db: Session = Depends(get_db), session: dict = Depends(require_instructor)):
    slots = db.query(Slot).filter(
        Slot.instructor_id == instructor_id,
        Slot.date >= week_start,
        Slot.date <= week_end
    ).order_by(Slot.date, Slot.time).all()
    result = []
    for s in slots:
        student_name = None
        if s.booked_by_student_id:
            student = db.query(Student).filter(Student.id == s.booked_by_student_id).first()
            student_name = student.full_name if student else "Неизвестно"
        result.append({
            "id": s.id,
            "date": str(s.date),
            "time": str(s.time),
            "is_booked": s.is_booked,
            "status": s.status,
            "student_name": student_name
        })
    return result


# Только для админа: студенты 
@router.get("/students/all")
def get_all_students(db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    students = db.query(Student).order_by(Student.id.desc()).all()
    return [
        {
            "id": s.id,
            "full_name": s.full_name,
            "identification_key": s.identification_key,
            "total_lessons": s.total_lessons,
            "used_lessons": s.used_lessons,
            "telegram_id": s.telegram_id or "не привязан"
        }
        for s in students
    ]


@router.post("/students/create")
def create_student(full_name: str = Form(...), total_lessons: int = Form(...), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    key = secrets.token_urlsafe(12)
    student = Student(
        full_name=full_name.strip(),
        total_lessons=total_lessons,
        used_lessons=0,
        identification_key=key
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"id": student.id, "full_name": student.full_name, "key": key}


@router.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    db.query(Slot).filter(Slot.booked_by_student_id == student_id).update(
        {"booked_by_student_id": None, "status": "free", "is_booked": False}
    )
    db.delete(student)
    db.commit()
    return {"message": "Удалён"}


@router.post("/students/{student_id}/reset-telegram")
def reset_telegram(student_id: int, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    """
    Отвязывает Telegram-аккаунт от ученика (например, если он сменил телефон/аккаунт
    и бот перестал его узнавать). После сброса ученик снова вводит свой ключ в боте
    и привязывается заново — уже к новому аккаунту.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    student.telegram_id = None
    db.commit()
    return {"message": "Telegram отвязан, ученик может привязаться заново"}

@router.post("/students/{student_id}/add-lessons")
def add_lessons(student_id: int, amount: int = Form(...), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    student.total_lessons += amount
    db.commit()
    return {"message": f"Добавлено {amount} занятий", "total_lessons": student.total_lessons}
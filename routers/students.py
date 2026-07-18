from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Student, Slot, Instructor
from schemas import StudentOut, StudentIdentify

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/identify", response_model=StudentOut)
def identify(data: StudentIdentify, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.identification_key == data.key).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ключ не найден")

    # Если этот Telegram уже привязан к ДРУГОМУ ученику — не даём тихо упасть
    # в UniqueViolation, а возвращаем понятную ошибку, которую бот покажет пользователю с просьбой обратиться к администратору.
    conflict = db.query(Student).filter(
        Student.telegram_id == data.telegram_id,
        Student.id != student.id
    ).first()
    if conflict:
        raise HTTPException(
            status_code=409,
            detail="Этот Telegram уже привязан к другому ученику. Обратитесь к администратору, чтобы отвязать старый аккаунт."
        )

    student.telegram_id = data.telegram_id
    db.commit()
    return student

@router.get("/by-telegram/{telegram_id}")
def get_by_telegram(telegram_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.telegram_id == telegram_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Не найден")
    return student


@router.get("/{student_id}/status")
def get_status(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    active_slot = db.query(Slot).filter(
        Slot.booked_by_student_id == student_id,
        Slot.status.in_(["pending", "confirmed"])
    ).first()
    return {
        "full_name": student.full_name,
        "total_lessons": student.total_lessons,
        "used_lessons": student.used_lessons,
        "active_slot": {
            "date": active_slot.date,
            "time": active_slot.time,
            "status": active_slot.status
        } if active_slot else None
    }

@router.get("/{student_id}/bookings")
def get_bookings(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")

    slots = db.query(Slot).filter(
        Slot.booked_by_student_id == student_id,
        Slot.status.in_(["pending", "confirmed"])
    ).all()
    if not slots:
        return []   

    result = []
    for slot in slots:
        instructor = db.query(Instructor).filter(Instructor.id == slot.instructor_id).first()
        result.append({
            "slot_id": slot.id,
            "date": str(slot.date),
            "time": str(slot.time),
            "instructor": instructor.full_name,
            "car_model": instructor.car_model,
            "kpp": instructor.transmission_type,
            "status": slot.status
        })

    return result
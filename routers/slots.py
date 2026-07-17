from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Slot, Student
from schemas import SlotOut, BookingCreate
import datetime 
import datetime as dt

router = APIRouter(prefix="/slots", tags=["slots"])

@router.get("/free/{instructor_id}", response_model=list[SlotOut])
def get_free_slots(instructor_id: int, date: datetime.date, db: Session = Depends(get_db)):
    return db.query(Slot).filter(
        Slot.instructor_id == instructor_id,
        Slot.date == date,
        Slot.is_booked == False
    ).order_by(Slot.time).all()

@router.post("/book")
def book_slot(data: BookingCreate, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.id == data.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Слот уже занят")
    
    active_count = db.query(Slot).filter(
        Slot.booked_by_student_id == data.student_id,
        Slot.status.in_(["pending", "confirmed"])
    ).count()
    if active_count >= 3:
        raise HTTPException(status_code=403, detail="Достигнут лимит записей (3)")
    
    slot.is_booked = True
    slot.status = "pending"
    slot.booked_by_student_id = data.student_id
    db.commit()
    return {"message": "Запись оформлена"}


@router.get("/week/{instructor_id}", response_model=list[SlotOut])
def get_week_slots(instructor_id: int, week_start: datetime.date, week_end: datetime.date, db: Session = Depends(get_db)):
    return db.query(Slot).filter(
        Slot.instructor_id == instructor_id,
        Slot.date >= week_start,
        Slot.date <= week_end,
        Slot.is_booked == False
    ).all()

@router.get("/{slot_id}", response_model=SlotOut)
def get_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Слот не найден")
    return slot

@router.post("/cancel_by_id/{slot_id}")
def cancel_by_id(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    slot_datetime = dt.datetime.combine(slot.date, slot.time)
    hours_left = (slot_datetime - dt.datetime.now()).total_seconds() / 3600

    charged = False
    if hours_left < 24:
        # отмена позже чем за 24 часа — по договору занятие списывается
        student = db.query(Student).filter(Student.id == slot.booked_by_student_id).first()
        if student:
            student.used_lessons += 1
        charged = True

    slot.is_booked = False
    slot.status = "cancelled_late" if charged else "free"
    slot.booked_by_student_id = None
    db.commit()
    return {"message": "Запись отменена", "charged": charged}
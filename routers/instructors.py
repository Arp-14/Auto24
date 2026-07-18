import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from passlib.context import CryptContext #type: ignore
from database import get_db
from models import Instructor, Slot
from schemas import InstructorOut
from .auth_simple import require_admin, create_session
import os 

router = APIRouter(prefix="/instructors", tags=["instructors"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PHOTO_DIR = os.environ.get("PHOTO_DIR", "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)


def _safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum())


# ── Публичные эндпоинты — их использует бот, авторизация не нужна ──

@router.get("/branch/{branch_id}", response_model=list[InstructorOut])
def get_by_branch(branch_id: int, db: Session = Depends(get_db)):
    instructors = db.query(Instructor).filter(Instructor.branch_id == branch_id).all()
    if not instructors:
        raise HTTPException(status_code=404, detail="Инструкторы не найдены")
    return instructors


@router.get("/{instructor_id}", response_model=InstructorOut)
def get_instructor(instructor_id: int, db: Session = Depends(get_db)):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Инструктор не найден")
    return instructor


# ── Вход инструктора в свою панель ──

@router.post("/login")
def instructor_login(instructor_id: int = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor or not instructor.password_hash or not pwd_context.verify(password, instructor.password_hash):
        raise HTTPException(status_code=401, detail="Неверный ID или пароль")
    token = create_session("instructor", instructor.id)
    return {"token": token, "role": "instructor", "instructor_id": instructor.id, "full_name": instructor.full_name}


# ── Управление инструкторами — только админ ──

@router.get("/", response_model=list[InstructorOut])
def get_all_instructors(db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    return db.query(Instructor).all()


@router.post("/create")
def create_instructor(
    full_name: str = Form(...),
    branch_id: int = Form(...),
    driving_since: int = Form(...),
    instructor_since: int = Form(...),
    car_model: str = Form(...),
    transmission_type: str = Form(...),
    password: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    filename = f"{_safe_filename(full_name)}_{photo.filename}"
    full_path = os.path.join(PHOTO_DIR, filename)
    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    instructor = Instructor(
        full_name=full_name,
        branch_id=branch_id,
        photo_path=f"photos/{filename}",
        driving_since=driving_since,
        instructor_since=instructor_since,
        car_model=car_model,
        transmission_type=transmission_type,
        password_hash=pwd_context.hash(password),
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return {"id": instructor.id, "full_name": instructor.full_name, "photo_path": instructor.photo_path}


@router.put("/{instructor_id}")
def update_instructor(
    instructor_id: int,
    full_name: str = Form(...),
    branch_id: int = Form(...),
    driving_since: int = Form(...),
    instructor_since: int = Form(...),
    car_model: str = Form(...),
    transmission_type: str = Form(...),
    photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Инструктор не найден")

    instructor.full_name = full_name
    instructor.branch_id = branch_id
    instructor.driving_since = driving_since
    instructor.instructor_since = instructor_since
    instructor.car_model = car_model
    instructor.transmission_type = transmission_type

    if photo:
        filename = f"{_safe_filename(full_name)}_{photo.filename}"
        full_path = os.path.join(PHOTO_DIR, filename)
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        instructor.photo_path = f"photos/{filename}"

    db.commit()
    return {"message": "Обновлено"}


@router.delete("/{instructor_id}")
def delete_instructor(instructor_id: int, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Инструктор не найден")
    
    db.query(Slot).filter(Slot.instructor_id == instructor.id).delete()

    db.delete(instructor)
    db.commit()
    return {"message": "Удалён вместе с его расписанием"}

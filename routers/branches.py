from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Branch
from schemas import BranchOut
from .auth_simple import require_admin

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("/", response_model=list[BranchOut])
def get_branches(db: Session = Depends(get_db)):
    # публичный эндпоинт — его использует бот
    return db.query(Branch).all()


@router.post("/create")
def create_branch(name: str = Form(...), db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    branch = Branch(name=name.strip())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return {"id": branch.id, "name": branch.name}


@router.delete("/{branch_id}")
def delete_branch(branch_id: int, db: Session = Depends(get_db), admin: dict = Depends(require_admin)):
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Отделение не найдено")
    if branch.instructors:
        raise HTTPException(
            status_code=400,
            detail="Сначала перепривяжите или удалите инструкторов этого отделения"
        )
    db.delete(branch)
    db.commit()
    return {"message": "Удалено"}

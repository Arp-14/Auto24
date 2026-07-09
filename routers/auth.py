from fastapi import APIRouter, Depends
from .auth_simple import get_current_session

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(session: dict = Depends(get_current_session)):
    # Фронт дергает этот эндпоинт при загрузке страницы, чтобы понять,
    # жив ли токен из localStorage, и какая роль у пользователя.
    return {"role": session["role"], "id": session["id"]}

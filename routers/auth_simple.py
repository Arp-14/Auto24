import secrets
from fastapi import Header, HTTPException, Depends

SESSIONS: dict[str, dict] = {}

ADMIN_PASSWORD = "2026"  # обязательно смени перед деплоем, лучше вынести в .env

def create_session(role: str, user_id: int | None = None) -> str:
    token = secrets.token_urlsafe(24)
    SESSIONS[token] = {"role": role, "id": user_id}
    return token

def get_current_session(authorization: str = Header(...)) -> dict:
    # Ожидаем заголовок: Authorization: Bearer <token>
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Нет токена")
    token = authorization.split(" ")[1]
    session = SESSIONS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Сессия недействительна, войдите заново")
    return session

def require_admin(session: dict = Depends(get_current_session)) -> dict:
    if session["role"] != "admin":
        raise HTTPException(status_code=403, detail="Только для администратора")
    return session

def require_instructor(session: dict = Depends(get_current_session)) -> dict:
    if session["role"] != "instructor":
        raise HTTPException(status_code=403, detail="Только для инструктора")
    return session
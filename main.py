import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine
from models import Base
from routers import branches, instructors, slots, students, admin, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auto24 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(branches.router)
app.include_router(instructors.router)
app.include_router(slots.router)
app.include_router(students.router)
app.include_router(admin.router)
app.include_router(auth.router)

# Фото инструкторов — раздаём по HTTP, чтобы фронт мог их показывать
os.makedirs("photos", exist_ok=True)
app.mount("/photos", StaticFiles(directory="photos"), name="photos")

# Общая статика фронта (css/js)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Сами HTML-страницы фронта — раздаём как статику из frontend/, на отдельном
# префиксе /app, чтобы не пересекаться с API-путями вроде /admin/...
os.makedirs("frontend", exist_ok=True)
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")

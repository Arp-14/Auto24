from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    instructors = relationship("Instructor", back_populates="branch")

class Instructor(Base):
    __tablename__ = "instructors"
    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id"))
    full_name = Column(String, nullable=False)
    photo_path = Column(String, nullable=False)
    driving_since = Column(Integer)
    instructor_since = Column(Integer)
    car_model = Column(String)
    transmission_type = Column(String)
    max_weeks_ahead = Column(Integer, default=2)
    default_reject_message = Column(String, default="К сожалению, вынужден отменить занятие. Приношу извинения.") 
    password_hash = Column(String, nullable=True) 
    branch = relationship("Branch", back_populates="instructors")

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    full_name = Column(String)
    identification_key = Column(String, unique=True)
    total_lessons = Column(Integer, default=16)
    used_lessons = Column(Integer, default=0)

class Slot(Base):
    __tablename__ = "slots"
    id = Column(Integer, primary_key=True)
    instructor_id = Column(Integer, ForeignKey("instructors.id"))
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    is_booked = Column(Boolean, default=False)
    booked_by_student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    status = Column(String, default="free")
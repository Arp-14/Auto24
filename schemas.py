from pydantic import BaseModel
from datetime import date, time

class BranchOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class InstructorOut(BaseModel):
    id: int
    full_name: str
    photo_path: str
    driving_since: int
    instructor_since: int
    car_model: str
    transmission_type: str
    max_weeks_ahead: int
    branch_id: int | None = None
    class Config:
        from_attributes = True

class SlotOut(BaseModel):
    id: int
    instructor_id: int 
    date: date
    time: time
    is_booked: bool
    status: str
    class Config:
        from_attributes = True

class StudentOut(BaseModel):
    id: int
    full_name: str
    total_lessons: int
    used_lessons: int
    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    slot_id: int
    student_id: int

class StudentIdentify(BaseModel):
    key: str
    telegram_id: str

class RejectBooking(BaseModel):
    message: str | None = None 

class UpdateDefaultMessage(BaseModel):
    message: str

class PendingSlotOut(BaseModel):
    id: int
    date: date
    time: time
    student_name: str
    class Config:
        from_attributes = True
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List, Optional
from pydantic import BaseModel
import redis
import json
import sys
import os

sys.path.insert(0, '/app/shared')
from shared.models import Student

app = FastAPI(title="Students Service")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# ============ PYDANTIC MODELS ============

class StudentUpdate(BaseModel):
    """Model for partial student updates - all fields optional"""
    name: Optional[str] = None
    completed_courses: Optional[List[str]] = None

# ============ ENDPOINTS ============

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "students"}


@app.get("/students", response_model=List[Student])
def list_students(session: Session = Depends(get_session)):
    """
    GET /students - List all students
    Returns: Array of all students
    """
    students = session.exec(select(Student)).all()
    return students


@app.get("/students/{student_id}", response_model=Student)
def get_student(student_id: int, session: Session = Depends(get_session)):
    """
    GET /students/{student_id} - Get student details (CACHED)

    Cache-Aside Pattern:
    1. Check Redis cache first
    2. If cache miss, query database
    3. Store result in cache (TTL: 300 seconds)
    4. Return student

    Why cache?
    - Every enrollment checks student's completed_courses
    - High read volume during registration
    - completed_courses rarely changes (only when course is completed)
    """
    # Try to get from Redis cache first
    cached_data = redis_client.get(f"student:{student_id}")
    if cached_data:
        return json.loads(cached_data)

    # Cache miss - query database
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Store in Redis cache with 300 second TTL
    redis_client.setex(f"student:{student_id}", 300, json.dumps(student.dict()))
    return student


@app.post("/students", response_model=Student, status_code=201)
def create_student(student: Student, session: Session = Depends(get_session)):
    """
    POST /students - Create a new student

    Request body:
    {
        "name": "John Doe",
        "completed_courses": ["CS187", "CS220"]
    }

    Returns: Created student with assigned ID
    """
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@app.put("/students/{student_id}", response_model=Student)
def update_student(
    student_id: int,
    student_update: StudentUpdate,
    session: Session = Depends(get_session)
):
    """
    PUT /students/{student_id} - Update student details (partial updates supported)

    Used to:
    - Add completed courses after semester ends
    - Update student name

    All fields are optional - only provided fields will be updated.

    IMPORTANT: Invalidate cache after update
    """
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Update only provided fields
    update_data = student_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    session.add(student)
    session.commit()
    session.refresh(student)

    # Invalidate cache
    redis_client.delete(f"student:{student_id}")

    return student


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, session: Session = Depends(get_session)):
    """
    DELETE /students/{student_id} - Delete a student

    IMPORTANT: Invalidate cache after deletion
    """
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    session.delete(student)
    session.commit()

    # Invalidate cache
    redis_client.delete(f"student:{student_id}")

    return None
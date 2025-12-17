from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List
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
    # TODO: Query all students from database
    pass


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
    # TODO:
    # 1. Try Redis: redis_client.get(f"student:{student_id}")
    # 2. If cache hit, return json.loads(cached_data)
    # 3. If cache miss:
    #    - Query database
    #    - Cache result: redis_client.setex(f"student:{student_id}", 300, json.dumps(student.dict()))
    # 4. Return student
    pass


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
    # TODO:
    # 1. Add student to database
    # 2. Commit and refresh
    # 3. Return created student
    pass


@app.put("/students/{student_id}", response_model=Student)
def update_student(
    student_id: int, 
    student_update: Student, 
    session: Session = Depends(get_session)
):
    """
    PUT /students/{student_id} - Update student details
    
    Used to:
    - Add completed courses after semester ends
    - Update student name
    
    IMPORTANT: Invalidate cache after update
    """
    # TODO:
    # 1. Get student from database
    # 2. Update fields (name, completed_courses)
    # 3. Commit changes
    # 4. Invalidate cache: redis_client.delete(f"student:{student_id}")
    # 5. Return updated student
    pass


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, session: Session = Depends(get_session)):
    """
    DELETE /students/{student_id} - Delete a student
    
    IMPORTANT: Invalidate cache after deletion
    """
    # TODO:
    # 1. Get student from database
    # 2. Delete student
    # 3. Commit transaction
    # 4. Invalidate cache: redis_client.delete(f"student:{student_id}")
    # 5. Return 204 No Content
    pass
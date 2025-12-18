from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List, Optional
from pydantic import BaseModel
import redis
import json
import os
import sys
sys.path.insert(0, '/app/shared')
from shared.models import Course

app = FastAPI(title="Courses Service")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Redis setup
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

# Create tables on startup
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# ============ PYDANTIC MODELS ============

class CourseUpdate(BaseModel):
    """Model for partial course updates - all fields optional"""
    name: Optional[str] = None
    code: Optional[str] = None
    capacity: Optional[int] = None
    enrolled: Optional[int] = None
    prerequisites: Optional[List[str]] = None

# ============ ENDPOINTS ============

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "courses"}


@app.get("/courses", response_model=List[Course])
def list_courses(session: Session = Depends(get_session)):
    """
    GET /courses - List all courses
    Returns: Array of all courses in the catalog
    No caching (list changes frequently with enrollments)
    """
    courses = session.exec(select(Course)).all()
    return courses


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: int, session: Session = Depends(get_session)):
    """
    GET /courses/{course_id} - Get course details (CACHED)

    Cache-Aside Pattern:
    1. Check Redis cache first
    2. If cache miss, query database
    3. Store result in cache (TTL: 300 seconds)
    4. Return course

    Why cache? High read volume during enrollment, course details rarely change
    """
    # Try to get from Redis cache first
    cached_data = redis_client.get(f"course:{course_id}")
    if cached_data:
        return json.loads(cached_data)

    # Cache miss - query database
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Store in Redis cache with 300 second TTL
    redis_client.setex(f"course:{course_id}", 300, json.dumps(course.dict()))
    return course


@app.post("/courses", response_model=Course, status_code=201)
def create_course(course: Course, session: Session = Depends(get_session)):
    """
    POST /courses - Create a new course

    Request body:
    {
        "name": "Web Systems",
        "code": "CS326",
        "capacity": 100,
        "prerequisites": ["CS220", "CS230"]
    }

    Returns: Created course with assigned ID
    """
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@app.put("/courses/{course_id}", response_model=Course)
def update_course(
    course_id: int,
    course_update: CourseUpdate,
    session: Session = Depends(get_session)
):
    """
    PUT /courses/{course_id} - Update course details (partial updates supported)

    Used to:
    - Update enrolled count when student enrolls
    - Update capacity
    - Update prerequisites

    All fields are optional - only provided fields will be updated.

    IMPORTANT: Invalidate cache after update
    """
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Update only provided fields
    update_data = course_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    session.add(course)
    session.commit()
    session.refresh(course)

    # Invalidate cache
    redis_client.delete(f"course:{course_id}")

    return course


@app.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, session: Session = Depends(get_session)):
    """
    DELETE /courses/{course_id} - Delete a course

    IMPORTANT: Invalidate cache after deletion
    """
    course = session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    session.delete(course)
    session.commit()

    # Invalidate cache
    redis_client.delete(f"course:{course_id}")

    return None
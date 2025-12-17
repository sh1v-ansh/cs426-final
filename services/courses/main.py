from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List, Optional
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
    # TODO: Query all courses from database
    # courses = session.exec(select(Course)).all()
    # return courses
    pass


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
    # TODO: 
    # 1. Try to get from Redis: redis_client.get(f"course:{course_id}")
    # 2. If found, return json.loads(cached_data)
    # 3. If not found:
    #    - Query database: session.get(Course, course_id)
    #    - Store in Redis: redis_client.setex(f"course:{course_id}", 300, json.dumps(course.dict()))
    #    - Return course
    # 4. If course not found, raise HTTPException(404)
    pass


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
    # TODO:
    # 1. Add course to database
    # 2. Commit transaction
    # 3. Refresh to get ID
    # 4. Return created course
    pass


@app.put("/courses/{course_id}", response_model=Course)
def update_course(
    course_id: int, 
    course_update: Course, 
    session: Session = Depends(get_session)
):
    """
    PUT /courses/{course_id} - Update course details
    
    Used to:
    - Update enrolled count when student enrolls
    - Update capacity
    - Update prerequisites
    
    IMPORTANT: Invalidate cache after update
    """
    # TODO:
    # 1. Get course from database
    # 2. Update fields (enrolled, capacity, etc.)
    # 3. Commit changes
    # 4. Invalidate cache: redis_client.delete(f"course:{course_id}")
    # 5. Return updated course
    pass


@app.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, session: Session = Depends(get_session)):
    """
    DELETE /courses/{course_id} - Delete a course
    
    IMPORTANT: Invalidate cache after deletion
    """
    # TODO:
    # 1. Get course from database
    # 2. Delete course
    # 3. Commit transaction
    # 4. Invalidate cache: redis_client.delete(f"course:{course_id}")
    # 5. Return 204 No Content
    pass
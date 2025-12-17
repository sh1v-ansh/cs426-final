from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlmodel import SQLModel, Session, create_engine, select
from typing import List, Optional
from pydantic import BaseModel
import pika
import json
import os
import requests
import threading
import sys
sys.path.insert(0, '/app/shared')
from shared.models import Enrollment

app = FastAPI(title="Enrollment Service")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# RabbitMQ setup
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
COURSES_SERVICE = os.getenv("COURSES_SERVICE_URL")
STUDENTS_SERVICE = os.getenv("STUDENTS_SERVICE_URL")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    # Start RabbitMQ consumer in background thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

def get_session():
    with Session(engine) as session:
        yield session

def get_rabbitmq_channel():
    """Create RabbitMQ connection and channel"""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='enrollments', durable=True)
    return connection, channel

# ============ PYDANTIC MODELS FOR REQUESTS ============

class EnrollmentRequest(BaseModel):
    """Request body for enrollment"""
    student_id: int
    course_id: int

class EnrollmentResponse(BaseModel):
    """Response for async enrollment"""
    status: str
    message: str
    enrollment_id: Optional[int] = None

# ============ ENDPOINTS ============

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "enrollment"}


@app.post("/enroll", response_model=EnrollmentResponse, status_code=202)
def enroll_student(request: EnrollmentRequest):
    """
    POST /enroll - Enroll a student in a course (ASYNC via RabbitMQ)

    Request body:
    {
        "student_id": 1,
        "course_id": 5
    }

    Process:
    1. Fetch student from Students Service (inter-service communication)
    2. Fetch course from Courses Service (inter-service communication)
    3. Validate prerequisites: Check if all course.prerequisites are in student.completed_courses
    4. Validate capacity: Check if course.enrolled < course.capacity
    5. If valid, publish message to RabbitMQ queue
    6. Return 202 Accepted (enrollment is being processed asynchronously)

    Returns: {"status": "pending", "message": "Enrollment queued for processing"}

    Why async?
    - Enrollment might take time (updating multiple DBs)
    - Prevents blocking during high traffic
    - Demonstrates resilience to spikes
    """
    # 1. Fetch student from Students Service
    try:
        student_response = requests.get(f"{STUDENTS_SERVICE}/students/{request.student_id}")
        student_response.raise_for_status()
        student = student_response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=404, detail="Student not found")

    # 2. Fetch course from Courses Service
    try:
        course_response = requests.get(f"{COURSES_SERVICE}/courses/{request.course_id}")
        course_response.raise_for_status()
        course = course_response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=404, detail="Course not found")

    # 3. Validate prerequisites
    required = course.get("prerequisites", [])
    completed = student.get("completed_courses", [])
    if not all(req in completed for req in required):
        raise HTTPException(status_code=400, detail="Prerequisites not met")

    # 4. Validate capacity
    if course["enrolled"] >= course["capacity"]:
        raise HTTPException(status_code=400, detail="Course is full")

    # 5. Publish to RabbitMQ
    connection, channel = get_rabbitmq_channel()
    message = json.dumps({"student_id": request.student_id, "course_id": request.course_id})
    channel.basic_publish(
        exchange='',
        routing_key='enrollments',
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    connection.close()

    # 6. Return 202 Accepted
    return EnrollmentResponse(
        status="pending",
        message="Enrollment queued for processing"
    )


@app.get("/enrollments", response_model=List[Enrollment])
def list_enrollments(session: Session = Depends(get_session)):
    """
    GET /enrollments - List all enrollments
    Returns: Array of all enrollment records
    """
    enrollments = session.exec(select(Enrollment)).all()
    return enrollments


@app.get("/enrollments/student/{student_id}", response_model=List[Enrollment])
def get_student_enrollments(student_id: int, session: Session = Depends(get_session)):
    """
    GET /enrollments/student/{student_id} - Get all enrollments for a student
    Returns: Array of enrollments for the specified student
    """
    enrollments = session.exec(
        select(Enrollment).where(Enrollment.student_id == student_id)
    ).all()
    return enrollments


@app.delete("/enrollments/{enrollment_id}", status_code=204)
def drop_enrollment(enrollment_id: int, session: Session = Depends(get_session)):
    """
    DELETE /enrollments/{enrollment_id} - Drop a course (delete enrollment)

    Also needs to:
    1. Delete enrollment record
    2. Update course enrolled count (call Courses Service PUT endpoint)
    """
    # 1. Get enrollment from database
    enrollment = session.get(Enrollment, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    # 2. Get course_id from enrollment
    course_id = enrollment.course_id

    # 3. Delete enrollment
    session.delete(enrollment)
    session.commit()

    # 4. Update course enrolled count (decrement by 1)
    try:
        # First get the current course data
        course_response = requests.get(f"{COURSES_SERVICE}/courses/{course_id}")
        course_response.raise_for_status()
        course = course_response.json()

        # Then update with decremented enrolled count
        requests.put(
            f"{COURSES_SERVICE}/courses/{course_id}",
            json={"enrolled": course["enrolled"] - 1}
        )
    except requests.exceptions.RequestException:
        # Log the error but don't fail the deletion
        pass

    return None


# ============ RABBITMQ CONSUMER (Background Worker) ============

def process_enrollment_message(ch, method, properties, body):
    """
    RabbitMQ consumer callback - processes enrollment messages from queue

    This runs in a background thread and processes queued enrollments

    Process:
    1. Parse message
    2. Create enrollment record in database
    3. Update course enrolled count via Courses Service
    4. Acknowledge message
    """
    try:
        # 1. Parse message
        data = json.loads(body)
        print(f"Processing enrollment: student_id={data['student_id']}, course_id={data['course_id']}")

        # 2. Create enrollment record in database
        with Session(engine) as session:
            enrollment = Enrollment(
                student_id=data["student_id"],
                course_id=data["course_id"]
            )
            session.add(enrollment)
            session.commit()
            print(f"Created enrollment record with ID: {enrollment.id}")

        # 3. Update course enrolled count (increment by 1)
        try:
            course_response = requests.get(f"{COURSES_SERVICE}/courses/{data['course_id']}")
            course_response.raise_for_status()
            course = course_response.json()

            requests.put(
                f"{COURSES_SERVICE}/courses/{data['course_id']}",
                json={"enrolled": course["enrolled"] + 1}
            )
            print(f"Updated course {data['course_id']} enrolled count to {course['enrolled'] + 1}")
        except requests.exceptions.RequestException as e:
            print(f"Error updating course enrolled count: {e}")

        # 4. Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("Enrollment processed successfully")

    except Exception as e:
        print(f"Error processing enrollment message: {e}")
        # Reject message and requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer():
    """Start RabbitMQ consumer in background thread"""
    connection, channel = get_rabbitmq_channel()
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue='enrollments',
        on_message_callback=process_enrollment_message
    )
    print("Starting RabbitMQ consumer...")
    channel.start_consuming()
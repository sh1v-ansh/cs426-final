# Mini-SPIRE: Scalable Course Enrollment System

A high-performance, microservices-based course enrollment system inspired by UMass Amherst's SPIRE. Built to handle traffic spikes during peak registration periods using caching, message queues, and horizontal scaling.

## Tech Stack

- **FastAPI**: REST API framework for all services
- **PostgreSQL**: Database-per-service pattern (3 instances)
- **Redis**: Cache-Aside pattern for read-heavy operations
- **RabbitMQ**: Asynchronous enrollment processing
- **NGINX**: API gateway and load balancer
- **Docker & Docker Compose**: Service orchestration and scaling
- **SQLModel**: ORM with Pydantic validation

## Architecture
```
Client → NGINX (Gateway) → FastAPI Services → PostgreSQL/Redis/RabbitMQ
                           ├─ Courses Service
                           ├─ Students Service  
                           └─ Enrollment Service
```

## Project Structure
```
mini-spire/
├── docker-compose.yml          # Service orchestration
├── requirements.txt            # Python dependencies
├── nginx/
│   └── nginx.conf             # API gateway & load balancing config
├── shared/
│   └── models.py              # SQLModel schemas (Student, Course, Enrollment)
├── services/
│   ├── courses/
│   │   ├── Dockerfile
│   │   └── main.py            # Course catalog service (CRUD + caching)
│   ├── students/
│   │   ├── Dockerfile
│   │   └── main.py            # Student records service (CRUD + caching)
│   └── enrollment/
│       ├── Dockerfile
│       └── main.py            # Enrollment orchestration (async processing)
└── tests/
    └── load_test.py           # Performance testing
```

## Services

### Courses Service (Port 8001)
- Manages course catalog (name, capacity, prerequisites)
- Implements Cache-Aside pattern for fast reads
- Provides CRUD endpoints

### Students Service (Port 8002)
- Manages student records and completed courses
- Implements Cache-Aside pattern for enrollment checks
- Provides CRUD endpoints

### Enrollment Service (Port 8003)
- Validates prerequisites and capacity
- Uses RabbitMQ for asynchronous enrollment processing
- Orchestrates inter-service communication
- Provides enrollment history endpoints

## How to Run

### Prerequisites
- Docker and Docker Compose installed

### Build and Start
```bash
# Build all services
docker-compose build

# Run with default scaling
docker-compose up

# Run with horizontal scaling (resilience demo)
docker-compose up --scale courses=3 --scale students=2 --scale enrollment=2
```

### Access Points
- **API Gateway**: http://localhost
- **Courses API**: http://localhost/courses
- **Students API**: http://localhost/students
- **Enrollment API**: http://localhost/enroll
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### Example Requests
```bash
# Create a course
curl -X POST http://localhost/courses \
  -H "Content-Type: application/json" \
  -d '{"name":"Web Systems","code":"CS326","capacity":100,"prerequisites":["CS220"]}'

# Create a student
curl -X POST http://localhost/students \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","completed_courses":["CS187","CS220"]}'

# Enroll student in course
curl -X POST http://localhost/enroll \
  -H "Content-Type: application/json" \
  -d '{"student_id":1,"course_id":1}'
```

### Stop Services
```bash
docker-compose down

# Remove volumes (reset databases)
docker-compose down -v
```

## Key Features

✅ **Microservices Architecture**: 3 independent FastAPI services
✅ **Database-per-Service**: Isolated PostgreSQL instances
✅ **Cache-Aside Pattern**: Redis caching reduces DB load by ~40-100x
✅ **Asynchronous Processing**: RabbitMQ handles enrollment spikes
✅ **Load Balancing**: NGINX distributes traffic across scaled instances
✅ **Horizontal Scaling**: `docker-compose up --scale` for resilience
✅ **Prerequisite Validation**: Automatic course requirement checking
✅ **Capacity Management**: Prevents course over-enrollment

## Performance Testing

Run load tests to measure latency and test failure resilience:
```bash
python tests/load_test.py
```

Simulate failures:
```bash
# Kill a service instance mid-test
docker-compose kill courses

# NGINX automatically routes to remaining instances
```
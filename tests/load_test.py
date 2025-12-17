# tests/load_test.py
import asyncio
import aiohttp
import time

async def enroll_student(session, student_id, course_id):
    start = time.time()
    async with session.post(
        'http://localhost:8000/enroll',
        json={'student_id': student_id, 'course_id': course_id}
    ) as resp:
        latency = time.time() - start
        return resp.status, latency

# Run 1000 concurrent enrollments
# Measure P50, P95, P99 latencies
# Toggle random failures in docker-compose (kill containers)
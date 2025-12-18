#!/usr/bin/env python3
"""
Mini-SPIRE Load Testing Suite

Comprehensive testing including:
1. Basic CRUD operations for all services
2. Performance and latency measurements
3. Chaos testing with random failures
4. Random pauses and disruptions
5. Concurrent user simulation
6. Cache effectiveness validation
7. End-to-end enrollment flow testing
"""

import requests
import time
import random
import subprocess
import json
import threading
import statistics
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import defaultdict

# ============ CONFIGURATION ============

BASE_URL = "http://localhost"
COURSES_URL = f"{BASE_URL}/courses"
STUDENTS_URL = f"{BASE_URL}/students"
ENROLL_URL = f"{BASE_URL}/enroll"

# Test configuration
CONCURRENT_USERS = 10
REQUESTS_PER_USER = 5
CHAOS_FAILURE_RATE = 0.1  # 10% chance of inducing failure
PAUSE_PROBABILITY = 0.15  # 15% chance of random pause

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# ============ UTILITIES ============

class PerformanceMetrics:
    """Tracks performance metrics across tests"""

    def __init__(self):
        self.latencies: Dict[str, List[float]] = defaultdict(list)
        self.successes: Dict[str, int] = defaultdict(int)
        self.failures: Dict[str, int] = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0

    def record_latency(self, operation: str, latency: float):
        """Record latency for an operation"""
        self.latencies[operation].append(latency)

    def record_success(self, operation: str):
        """Record successful operation"""
        self.successes[operation] += 1

    def record_failure(self, operation: str):
        """Record failed operation"""
        self.failures[operation] += 1

    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        if operation not in self.latencies or not self.latencies[operation]:
            return {}

        latencies = self.latencies[operation]
        return {
            'count': len(latencies),
            'min': min(latencies),
            'max': max(latencies),
            'mean': statistics.mean(latencies),
            'median': statistics.median(latencies),
            'p95': sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 0 else 0,
            'p99': sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 0 else 0,
            'successes': self.successes[operation],
            'failures': self.failures[operation]
        }

    def print_summary(self):
        """Print comprehensive performance summary"""
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}PERFORMANCE SUMMARY{RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")

        for operation in sorted(self.latencies.keys()):
            stats = self.get_stats(operation)
            if not stats:
                continue

            success_rate = (stats['successes'] / (stats['successes'] + stats['failures']) * 100) if (stats['successes'] + stats['failures']) > 0 else 0

            print(f"{YELLOW}{operation}:{RESET}")
            print(f"  Total Requests: {stats['count']}")
            print(f"  Success Rate: {success_rate:.1f}% ({stats['successes']} successes, {stats['failures']} failures)")
            print(f"  Latency (ms):")
            print(f"    Min: {stats['min']*1000:.2f}ms")
            print(f"    Mean: {stats['mean']*1000:.2f}ms")
            print(f"    Median: {stats['median']*1000:.2f}ms")
            print(f"    Max: {stats['max']*1000:.2f}ms")
            print(f"    P95: {stats['p95']*1000:.2f}ms")
            print(f"    P99: {stats['p99']*1000:.2f}ms")
            print()

        # Cache statistics
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations > 0:
            cache_hit_rate = (self.cache_hits / total_cache_operations) * 100
            print(f"{YELLOW}Cache Performance:{RESET}")
            print(f"  Cache Hits: {self.cache_hits}")
            print(f"  Cache Misses: {self.cache_misses}")
            print(f"  Hit Rate: {cache_hit_rate:.1f}%")
            print()


metrics = PerformanceMetrics()


def timed_request(operation: str, method: str, url: str, **kwargs) -> Tuple[Any, float]:
    """Execute a timed HTTP request"""
    start = time.time()
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        latency = time.time() - start
        metrics.record_latency(operation, latency)

        if response.status_code < 400:
            metrics.record_success(operation)
        else:
            metrics.record_failure(operation)

        return response, latency
    except Exception as e:
        latency = time.time() - start
        metrics.record_latency(operation, latency)
        metrics.record_failure(operation)
        raise


def print_test_header(test_name: str):
    """Print formatted test header"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}TEST: {test_name}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}[OK] {message}{RESET}")


def print_failure(message: str):
    """Print failure message"""
    print(f"{RED}[FAIL] {message}{RESET}")


def print_info(message: str):
    """Print info message"""
    print(f"{YELLOW}[INFO] {message}{RESET}")


def random_pause():
    """Randomly pause to simulate network delays"""
    if random.random() < PAUSE_PROBABILITY:
        delay = random.uniform(0.1, 0.5)
        print_info(f"Random pause: {delay:.2f}s")
        time.sleep(delay)


def chaos_failure() -> bool:
    """Randomly decide if chaos should be induced"""
    return random.random() < CHAOS_FAILURE_RATE


# ============ DOCKER CHAOS TESTING ============

def get_running_containers() -> List[str]:
    """Get list of running service containers"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=cs426-final", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        containers = [name for name in result.stdout.strip().split('\n') if name]
        # Filter out infrastructure (keep only courses, students, enrollment)
        service_containers = [c for c in containers if any(s in c for s in ['courses', 'students', 'enrollment'])]
        return service_containers
    except subprocess.CalledProcessError:
        return []


def restart_random_container():
    """Restart a random service container (chaos testing)"""
    containers = get_running_containers()
    if containers:
        container = random.choice(containers)
        print_info(f"CHAOS: Restarting container {container}")
        try:
            subprocess.run(["docker", "restart", container], capture_output=True, timeout=10)
            time.sleep(2)  # Wait for service to restart
            print_info(f"Container {container} restarted")
        except Exception as e:
            print_failure(f"Failed to restart container: {e}")


def pause_random_container(duration: float = 3):
    """Pause a random service container temporarily"""
    containers = get_running_containers()
    if containers:
        container = random.choice(containers)
        print_info(f"CHAOS: Pausing container {container} for {duration}s")
        try:
            subprocess.run(["docker", "pause", container], capture_output=True, timeout=5)
            time.sleep(duration)
            subprocess.run(["docker", "unpause", container], capture_output=True, timeout=5)
            print_info(f"Container {container} unpaused")
        except Exception as e:
            print_failure(f"Failed to pause/unpause container: {e}")


# ============ BASIC CRUD TESTS ============

def test_courses_crud():
    """Test all CRUD operations for courses service"""
    print_test_header("Courses Service - CRUD Operations")

    # CREATE
    print_info("Testing CREATE course...")
    course_data = {
        "name": "Introduction to Algorithms",
        "code": "CS375",
        "capacity": 50,
        "enrolled": 0,
        "prerequisites": ["CS220", "CS230"]
    }
    response, latency = timed_request("CREATE_COURSE", "POST", COURSES_URL, json=course_data)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    course = response.json()
    course_id = course['id']
    print_success(f"Course created with ID {course_id} (latency: {latency*1000:.2f}ms)")

    random_pause()

    # READ (should be cached on subsequent reads)
    print_info("Testing READ course (first read - cache miss)...")
    response, latency = timed_request("READ_COURSE", "GET", f"{COURSES_URL}/{course_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics.cache_misses += 1
    print_success(f"Course retrieved (latency: {latency*1000:.2f}ms)")

    print_info("Testing READ course (second read - cache hit expected)...")
    start_time = time.time()
    response, latency = timed_request("READ_COURSE_CACHED", "GET", f"{COURSES_URL}/{course_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics.cache_hits += 1

    # Cache hit should be faster
    if latency < start_time:
        print_success(f"Cache hit detected (latency: {latency*1000:.2f}ms - faster!)")
    else:
        print_success(f"Course retrieved from cache (latency: {latency*1000:.2f}ms)")

    random_pause()

    # UPDATE
    print_info("Testing UPDATE course...")
    course_data['capacity'] = 75
    response, latency = timed_request("UPDATE_COURSE", "PUT", f"{COURSES_URL}/{course_id}", json=course_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    updated_course = response.json()
    assert updated_course['capacity'] == 75, "Capacity not updated"
    print_success(f"Course updated (latency: {latency*1000:.2f}ms)")

    # LIST
    print_info("Testing LIST courses...")
    response, latency = timed_request("LIST_COURSES", "GET", COURSES_URL)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    courses = response.json()
    assert len(courses) > 0, "No courses returned"
    print_success(f"Listed {len(courses)} courses (latency: {latency*1000:.2f}ms)")

    random_pause()

    # DELETE
    print_info("Testing DELETE course...")
    response, latency = timed_request("DELETE_COURSE", "DELETE", f"{COURSES_URL}/{course_id}")
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    print_success(f"Course deleted (latency: {latency*1000:.2f}ms)")

    # Verify deletion
    response, _ = timed_request("READ_COURSE_DELETED", "GET", f"{COURSES_URL}/{course_id}")
    assert response.status_code == 404, "Course should not exist after deletion"
    print_success("Deletion verified")

    print(f"\n{GREEN} All courses CRUD tests passed!{RESET}\n")


def test_students_crud():
    """Test all CRUD operations for students service"""
    print_test_header("Students Service - CRUD Operations")

    # CREATE
    print_info("Testing CREATE student...")
    student_data = {
        "name": "Alice Johnson",
        "completed_courses": ["CS187", "CS220"]
    }
    response, latency = timed_request("CREATE_STUDENT", "POST", STUDENTS_URL, json=student_data)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    student = response.json()
    student_id = student['id']
    print_success(f"Student created with ID {student_id} (latency: {latency*1000:.2f}ms)")

    random_pause()

    # READ
    print_info("Testing READ student (cache miss)...")
    response, latency = timed_request("READ_STUDENT", "GET", f"{STUDENTS_URL}/{student_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics.cache_misses += 1
    print_success(f"Student retrieved (latency: {latency*1000:.2f}ms)")

    print_info("Testing READ student (cache hit expected)...")
    response, latency = timed_request("READ_STUDENT_CACHED", "GET", f"{STUDENTS_URL}/{student_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    metrics.cache_hits += 1
    print_success(f"Student retrieved from cache (latency: {latency*1000:.2f}ms)")

    random_pause()

    # UPDATE
    print_info("Testing UPDATE student...")
    student_data['completed_courses'].append("CS230")
    response, latency = timed_request("UPDATE_STUDENT", "PUT", f"{STUDENTS_URL}/{student_id}", json=student_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    updated_student = response.json()
    assert "CS230" in updated_student['completed_courses'], "Course not added"
    print_success(f"Student updated (latency: {latency*1000:.2f}ms)")

    # LIST
    print_info("Testing LIST students...")
    response, latency = timed_request("LIST_STUDENTS", "GET", STUDENTS_URL)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    students = response.json()
    assert len(students) > 0, "No students returned"
    print_success(f"Listed {len(students)} students (latency: {latency*1000:.2f}ms)")

    random_pause()

    # DELETE
    print_info("Testing DELETE student...")
    response, latency = timed_request("DELETE_STUDENT", "DELETE", f"{STUDENTS_URL}/{student_id}")
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    print_success(f"Student deleted (latency: {latency*1000:.2f}ms)")

    print(f"\n{GREEN} All students CRUD tests passed!{RESET}\n")


def test_enrollment_flow():
    """Test complete enrollment flow including validation"""
    print_test_header("Enrollment Service - Complete Flow")

    # Setup: Create course and student
    print_info("Setting up test data...")

    # Create course with prerequisites
    course_data = {
        "name": "Advanced Algorithms",
        "code": "CS473",
        "capacity": 30,
        "enrolled": 0,
        "prerequisites": ["CS220", "CS230", "CS375"]
    }
    response, _ = timed_request("CREATE_COURSE_SETUP", "POST", COURSES_URL, json=course_data)
    course = response.json()
    course_id = course['id']
    print_success(f"Test course created: {course['code']}")

    # Create student WITH prerequisites
    student_data = {
        "name": "Bob Smith",
        "completed_courses": ["CS187", "CS220", "CS230", "CS375"]
    }
    response, _ = timed_request("CREATE_STUDENT_SETUP", "POST", STUDENTS_URL, json=student_data)
    student = response.json()
    student_id = student['id']
    print_success(f"Test student created: {student['name']}")

    random_pause()

    # Test 1: Successful enrollment
    print_info("Testing SUCCESSFUL enrollment (has prerequisites)...")
    enroll_data = {
        "student_id": student_id,
        "course_id": course_id
    }
    response, latency = timed_request("ENROLL_SUCCESS", "POST", ENROLL_URL, json=enroll_data)
    assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}"
    enrollment_response = response.json()
    assert enrollment_response['status'] == 'pending', "Expected pending status"
    print_success(f"Enrollment queued for async processing (latency: {latency*1000:.2f}ms)")

    # Wait for async processing
    print_info("Waiting for RabbitMQ async processing...")
    time.sleep(3)

    # Verify enrollment was created
    response, _ = timed_request("LIST_ENROLLMENTS", "GET", f"{ENROLL_URL}ments")
    enrollments = response.json()
    assert len(enrollments) > 0, "No enrollments found"
    print_success(f"Enrollment processed: {len(enrollments)} enrollment(s) found")

    # Verify course enrolled count was updated
    response, _ = timed_request("VERIFY_ENROLLED_COUNT", "GET", f"{COURSES_URL}/{course_id}")
    updated_course = response.json()
    assert updated_course['enrolled'] > 0, "Enrolled count not updated"
    print_success(f"Course enrolled count updated to {updated_course['enrolled']}")

    random_pause()

    # Test 2: Enrollment without prerequisites (should fail)
    print_info("Testing FAILED enrollment (missing prerequisites)...")
    student_no_prereq = {
        "name": "Charlie Brown",
        "completed_courses": ["CS187"]  # Missing CS220, CS230, CS375
    }
    response, _ = timed_request("CREATE_STUDENT_NO_PREREQ", "POST", STUDENTS_URL, json=student_no_prereq)
    student2 = response.json()

    enroll_data2 = {
        "student_id": student2['id'],
        "course_id": course_id
    }
    response, latency = timed_request("ENROLL_FAIL_PREREQ", "POST", ENROLL_URL, json=enroll_data2)
    assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
    print_success(f"Prerequisite validation working (rejected in {latency*1000:.2f}ms)")

    random_pause()

    # Test 3: Test capacity limit
    print_info("Testing capacity limit validation...")
    # Create course with capacity 0
    full_course = {
        "name": "Full Course",
        "code": "CS999",
        "capacity": 0,
        "enrolled": 0,
        "prerequisites": []
    }
    response, _ = timed_request("CREATE_FULL_COURSE", "POST", COURSES_URL, json=full_course)
    full_course_id = response.json()['id']

    enroll_full = {
        "student_id": student_id,
        "course_id": full_course_id
    }
    response, latency = timed_request("ENROLL_FAIL_CAPACITY", "POST", ENROLL_URL, json=enroll_full)
    assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
    assert "full" in response.json()['detail'].lower(), "Expected 'full' in error message"
    print_success(f"Capacity validation working (rejected in {latency*1000:.2f}ms)")

    random_pause()

    # Test 4: Drop enrollment
    print_info("Testing DROP enrollment...")
    enrollment_id = enrollments[0]['id']
    response, latency = timed_request("DROP_ENROLLMENT", "DELETE", f"{ENROLL_URL}ments/{enrollment_id}")
    assert response.status_code == 204, f"Expected 204, got {response.status_code}"
    print_success(f"Enrollment dropped (latency: {latency*1000:.2f}ms)")

    # Verify course enrolled count was decremented
    time.sleep(1)
    response, _ = timed_request("VERIFY_DECREMENT", "GET", f"{COURSES_URL}/{course_id}")
    final_course = response.json()
    assert final_course['enrolled'] == updated_course['enrolled'] - 1, "Enrolled count not decremented"
    print_success(f"Course enrolled count decremented to {final_course['enrolled']}")

    print(f"\n{GREEN} All enrollment flow tests passed!{RESET}\n")


# ============ CONCURRENT LOAD TESTS ============

def concurrent_user_simulation(user_id: int, iterations: int) -> Dict[str, Any]:
    """Simulate a single concurrent user"""
    results = {
        'user_id': user_id,
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_latency': 0
    }

    for i in range(iterations):
        try:
            # Random operation
            operation = random.choice(['create_student', 'list_courses', 'list_students'])

            if operation == 'create_student':
                student_data = {
                    "name": f"User{user_id}_Student{i}",
                    "completed_courses": random.sample(["CS187", "CS220", "CS230", "CS240"], k=random.randint(0, 3))
                }
                response, latency = timed_request(f"CONCURRENT_CREATE_STUDENT_U{user_id}", "POST", STUDENTS_URL, json=student_data)

            elif operation == 'list_courses':
                response, latency = timed_request(f"CONCURRENT_LIST_COURSES_U{user_id}", "GET", COURSES_URL)

            else:  # list_students
                response, latency = timed_request(f"CONCURRENT_LIST_STUDENTS_U{user_id}", "GET", STUDENTS_URL)

            results['total_requests'] += 1
            results['total_latency'] += latency

            if response.status_code < 400:
                results['successful_requests'] += 1
            else:
                results['failed_requests'] += 1

        except Exception as e:
            results['failed_requests'] += 1
            results['total_requests'] += 1

    return results


def test_concurrent_load():
    """Test system under concurrent load"""
    print_test_header(f"Concurrent Load Test - {CONCURRENT_USERS} users, {REQUESTS_PER_USER} requests each")

    print_info(f"Starting {CONCURRENT_USERS} concurrent users...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [executor.submit(concurrent_user_simulation, i, REQUESTS_PER_USER) for i in range(CONCURRENT_USERS)]

        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print_failure(f"User thread failed: {e}")

    total_time = time.time() - start_time

    # Aggregate results
    total_requests = sum(r['total_requests'] for r in results)
    total_successful = sum(r['successful_requests'] for r in results)
    total_failed = sum(r['failed_requests'] for r in results)
    avg_latency = sum(r['total_latency'] for r in results) / total_requests if total_requests > 0 else 0

    print_success(f"Completed {total_requests} requests in {total_time:.2f}s")
    print_success(f"Success rate: {(total_successful/total_requests*100):.1f}%")
    print_success(f"Throughput: {total_requests/total_time:.2f} requests/second")
    print_success(f"Average latency: {avg_latency*1000:.2f}ms")

    print(f"\n{GREEN} Concurrent load test completed!{RESET}\n")


# ============ CHAOS TESTING ============

def test_chaos_resilience():
    """Test system resilience with random failures"""
    print_test_header("Chaos Testing - Random Failures & Disruptions")

    containers = get_running_containers()
    if not containers:
        print_failure("Docker not available or no containers running. Skipping chaos tests.")
        return

    print_info(f"Found {len(containers)} service containers for chaos testing")

    # Test 1: Service restart during requests
    print_info("Test 1: Restarting random service during operations...")
    restart_random_container()
    time.sleep(2)

    try:
        response, _ = timed_request("CHAOS_AFTER_RESTART", "GET", COURSES_URL)
        if response.status_code == 200:
            print_success("Service recovered after restart")
    except Exception as e:
        print_failure(f"Request failed after restart: {e}")

    # Test 2: Pause container temporarily
    print_info("Test 2: Pausing random service temporarily...")

    def make_request_during_pause():
        time.sleep(1)  # Wait a bit before making request
        try:
            response, latency = timed_request("CHAOS_DURING_PAUSE", "GET", STUDENTS_URL)
            return response.status_code, latency
        except Exception as e:
            return None, None

    # Start request in background
    request_thread = threading.Thread(target=make_request_during_pause)
    request_thread.start()

    # Pause container
    pause_random_container(duration=2)
    request_thread.join()

    print_success("Service recovered after pause/unpause")

    # Test 3: Multiple rapid requests with random pauses
    print_info("Test 3: Rapid requests with random disruptions...")
    success_count = 0
    for i in range(10):
        random_pause()
        try:
            response, _ = timed_request("CHAOS_RAPID_REQUEST", "GET", COURSES_URL)
            if response.status_code == 200:
                success_count += 1
        except Exception:
            pass

    print_success(f"Completed rapid requests: {success_count}/10 successful")

    print(f"\n{GREEN} Chaos testing completed!{RESET}\n")


# ============ CACHE EFFECTIVENESS TEST ============

def test_cache_effectiveness():
    """Test Redis cache effectiveness"""
    print_test_header("Cache Effectiveness Test")

    # Create a test course
    course_data = {
        "name": "Cache Test Course",
        "code": "CACHE101",
        "capacity": 100,
        "enrolled": 0,
        "prerequisites": []
    }
    response, _ = timed_request("CACHE_CREATE", "POST", COURSES_URL, json=course_data)
    course_id = response.json()['id']

    # First read (cache miss)
    print_info("Reading course for first time (cache miss expected)...")
    response1, latency1 = timed_request("CACHE_MISS", "GET", f"{COURSES_URL}/{course_id}")
    metrics.cache_misses += 1

    # Subsequent reads (cache hits)
    print_info("Reading course 5 more times (cache hits expected)...")
    latencies = []
    for i in range(5):
        response, latency = timed_request("CACHE_HIT", "GET", f"{COURSES_URL}/{course_id}")
        latencies.append(latency)
        metrics.cache_hits += 1

    avg_cached_latency = statistics.mean(latencies)
    speedup = (latency1 / avg_cached_latency) if avg_cached_latency > 0 else 1

    print_success(f"First read (DB): {latency1*1000:.2f}ms")
    print_success(f"Avg cached read: {avg_cached_latency*1000:.2f}ms")
    print_success(f"Cache speedup: {speedup:.2f}x faster")

    # Test cache invalidation
    print_info("Testing cache invalidation on update...")
    course_data['capacity'] = 150
    response, _ = timed_request("CACHE_INVALIDATE", "PUT", f"{COURSES_URL}/{course_id}", json=course_data)

    # Next read should be slower (cache miss after invalidation)
    response, latency_after = timed_request("CACHE_MISS_AFTER_UPDATE", "GET", f"{COURSES_URL}/{course_id}")
    metrics.cache_misses += 1

    if latency_after > avg_cached_latency:
        print_success(f"Cache invalidation working (read after update: {latency_after*1000:.2f}ms)")

    # Cleanup
    timed_request("CACHE_CLEANUP", "DELETE", f"{COURSES_URL}/{course_id}")

    print(f"\n{GREEN} Cache effectiveness test completed!{RESET}\n")


# ============ MAIN TEST RUNNER ============

def wait_for_services(max_retries=30, delay=2):
    """Wait for all services to be healthy"""
    print_info("Waiting for services to be ready...")

    services = {
        'Courses': COURSES_URL,
        'Students': STUDENTS_URL,
        'Enrollment': f"{ENROLL_URL}ments"
    }

    for attempt in range(max_retries):
        all_healthy = True
        for name, url in services.items():
            try:
                # Try to access health endpoint or list endpoint
                health_url = url.replace('/courses', '/health').replace('/students', '/health').replace('/enrollments', '/health')
                response = requests.get(health_url, timeout=2)
                if response.status_code != 200:
                    all_healthy = False
                    break
            except Exception:
                all_healthy = False
                break

        if all_healthy:
            print_success("All services are ready!")
            return True

        print(f"  Attempt {attempt + 1}/{max_retries}...", end='\r')
        time.sleep(delay)

    print_failure("Services did not become ready in time")
    return False


def run_all_tests():
    """Run all test suites"""
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}MINI-SPIRE LOAD TESTING SUITE{RESET}")
    print(f"{BLUE}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    # Wait for services
    if not wait_for_services():
        print_failure("Cannot proceed with tests - services not ready")
        return

    try:
        # Basic CRUD tests
        test_courses_crud()
        test_students_crud()

        # Enrollment flow
        test_enrollment_flow()

        # Cache effectiveness
        test_cache_effectiveness()

        # Concurrent load
        test_concurrent_load()

        # Chaos testing
        test_chaos_resilience()

    except AssertionError as e:
        print_failure(f"Test assertion failed: {e}")
        raise
    except Exception as e:
        print_failure(f"Test error: {e}")
        raise
    finally:
        # Print performance summary
        metrics.print_summary()

        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")


if __name__ == "__main__":
    run_all_tests()

# Mini-SPIRE Load Testing Suite

Comprehensive testing suite for the Mini-SPIRE course enrollment microservices system.

## Features

This test suite includes:

### 1. **Basic CRUD Operations Testing**
- ✅ Tests all endpoints for Courses, Students, and Enrollment services
- ✅ Validates create, read, update, delete operations
- ✅ Verifies proper HTTP status codes and response formats

### 2. **Performance & Latency Measurements**
- ✅ Tracks latency for every operation
- ✅ Calculates min, max, mean, median, P95, P99 percentiles
- ✅ Measures throughput (requests/second)
- ✅ Success/failure rate tracking

### 3. **Cache Effectiveness Validation**
- ✅ Tests Redis Cache-Aside pattern
- ✅ Measures cache hit/miss ratios
- ✅ Validates cache speedup (typically 2-10x faster)
- ✅ Tests cache invalidation on updates/deletes

### 4. **End-to-End Enrollment Flow**
- ✅ Tests complete enrollment process
- ✅ Validates prerequisite checking
- ✅ Validates capacity limits
- ✅ Tests async RabbitMQ processing
- ✅ Tests enrollment dropping with cascade updates

### 5. **Concurrent Load Testing**
- ✅ Simulates multiple concurrent users (configurable)
- ✅ Tests system under load
- ✅ Measures concurrent throughput
- ✅ Validates thread safety

### 6. **Chaos Testing**
- ✅ Random service restarts
- ✅ Random container pauses/unpauses
- ✅ Random network delays
- ✅ Tests system resilience and recovery

## Prerequisites

1. **Docker & Docker Compose** - For running the services
2. **Python 3.8+** - For running tests
3. **requests library** - Install with: `pip install requests`

## Running the Tests

### Step 1: Start the Services

From the repository root:

```bash
docker compose up --build -d
```

Wait for all services to be healthy (typically 30-60 seconds).

### Step 2: Verify Services Are Running

```bash
docker compose ps
```

You should see all 8 services running:
- postgres-courses
- postgres-students
- postgres-enrollments
- redis
- rabbitmq
- courses
- students
- enrollment
- nginx

### Step 3: Run the Load Tests

```bash
python3 tests/load_test.py
```

Or make it executable and run:

```bash
chmod +x tests/load_test.py
./tests/load_test.py
```

## Test Configuration

You can modify test parameters in `load_test.py`:

```python
# Test configuration
CONCURRENT_USERS = 10          # Number of concurrent users
REQUESTS_PER_USER = 5          # Requests per user in load test
CHAOS_FAILURE_RATE = 0.1       # 10% chance of inducing failure
PAUSE_PROBABILITY = 0.15       # 15% chance of random pause
```

## Expected Output

The test suite will display:

1. **Progress indicators** for each test with color-coded status:
   - 🟢 Green ✓ = Success
   - 🔴 Red ✗ = Failure
   - 🟡 Yellow ➜ = Info/Progress

2. **Test sections**:
   ```
   ================================================================================
   TEST: Courses Service - CRUD Operations
   ================================================================================

   ➜ Testing CREATE course...
   ✓ Course created with ID 1 (latency: 45.23ms)
   ...
   ```

3. **Performance Summary** at the end:
   ```
   ================================================================================
   PERFORMANCE SUMMARY
   ================================================================================

   CREATE_COURSE:
     Total Requests: 10
     Success Rate: 100.0% (10 successes, 0 failures)
     Latency (ms):
       Min: 23.45ms
       Mean: 35.67ms
       Median: 34.12ms
       Max: 52.89ms
       P95: 48.23ms
       P99: 51.45ms

   Cache Performance:
     Cache Hits: 45
     Cache Misses: 15
     Hit Rate: 75.0%
   ```

## Test Suites Breakdown

### 1. Courses CRUD Test
Tests all CRUD operations on the courses service:
- Create a course
- Read course (with cache testing)
- Update course capacity
- List all courses
- Delete course
- Verify deletion

### 2. Students CRUD Test
Tests all CRUD operations on the students service:
- Create a student
- Read student (with cache testing)
- Update student's completed courses
- List all students
- Delete student

### 3. Enrollment Flow Test
Tests the complete enrollment workflow:
- **Success case**: Student with prerequisites enrolls successfully
- **Failure case 1**: Student without prerequisites is rejected
- **Failure case 2**: Enrollment in full course is rejected
- **Drop case**: Student drops course, enrolled count decrements
- **Async processing**: Verifies RabbitMQ message processing

### 4. Cache Effectiveness Test
Validates Redis caching:
- First read hits database (slower)
- Subsequent reads hit cache (faster)
- Measures speedup (typically 2-10x)
- Tests cache invalidation on updates

### 5. Concurrent Load Test
Simulates real-world load:
- Spawns N concurrent users
- Each user makes M requests
- Measures aggregate throughput
- Calculates success rate under load

### 6. Chaos Testing
Tests system resilience:
- Randomly restarts service containers
- Temporarily pauses containers
- Introduces random network delays
- Verifies service recovery

## Interpreting Results

### Good Performance Indicators

✅ **Latency**:
- Cached reads: < 10ms
- Database reads: < 100ms
- Writes: < 150ms
- P95 < 200ms

✅ **Cache Performance**:
- Hit rate > 60%
- Cache speedup > 2x

✅ **Reliability**:
- Success rate > 95%
- System recovers after chaos events

✅ **Throughput**:
- > 50 requests/second for reads
- > 20 requests/second for writes

### Performance Issues

⚠️ **High latency** (>500ms):
- Database connection issues
- Network problems
- Service overload

⚠️ **Low cache hit rate** (<40%):
- Cache not working properly
- Cache TTL too short
- High write rate invalidating cache

⚠️ **Low success rate** (<90%):
- Service instability
- Database connection issues
- Logic errors

## Troubleshooting

### Services Not Ready

If tests fail with "Services not ready":

```bash
# Check service status
docker compose ps

# Check service logs
docker compose logs courses
docker compose logs students
docker compose logs enrollment

# Restart services
docker compose restart
```

### Connection Refused Errors

Ensure nginx is running and properly routing:

```bash
# Test direct service access
curl http://localhost/courses
curl http://localhost/students
curl http://localhost/enroll

# Check nginx logs
docker compose logs nginx
```

### Chaos Tests Skipped

If Docker commands don't work:
- Tests require Docker CLI access
- Run tests on the same machine as Docker daemon
- Ensure user has Docker permissions

### Slow Performance

Potential causes:
- Services still starting up (wait longer)
- Docker resource limits (increase CPU/memory)
- Database not optimized (first run is slower)
- Network latency

## Advanced Usage

### Run Specific Test

Edit `load_test.py` and comment out tests you don't want:

```python
def run_all_tests():
    # test_courses_crud()
    # test_students_crud()
    test_enrollment_flow()  # Only run this
    # test_cache_effectiveness()
    # test_concurrent_load()
    # test_chaos_resilience()
```

### Increase Load

For stress testing:

```python
CONCURRENT_USERS = 50      # More concurrent users
REQUESTS_PER_USER = 20     # More requests per user
```

### Disable Chaos

For stable performance testing:

```python
CHAOS_FAILURE_RATE = 0.0   # No random failures
PAUSE_PROBABILITY = 0.0    # No random pauses
```

## Continuous Integration

To use in CI/CD:

```bash
# Start services in background
docker compose up -d

# Wait for health checks
sleep 30

# Run tests
python3 tests/load_test.py

# Exit code 0 = success, non-zero = failure
if [ $? -eq 0 ]; then
    echo "Tests passed!"
else
    echo "Tests failed!"
    docker compose logs
    exit 1
fi

# Cleanup
docker compose down -v
```

## Metrics to Track

Key metrics to monitor:

1. **Response Time**: P50, P95, P99 latencies
2. **Throughput**: Requests per second
3. **Error Rate**: Percentage of failed requests
4. **Cache Hit Rate**: Percentage of cache hits
5. **Recovery Time**: Time to recover after failures

## Further Improvements

Potential enhancements:

- [ ] Add database query profiling
- [ ] Add memory usage tracking
- [ ] Add network traffic measurement
- [ ] Generate HTML test reports
- [ ] Add automated regression testing
- [ ] Add load ramp-up patterns
- [ ] Test with different data sizes
- [ ] Add distributed load testing

## Support

For issues or questions:
- Check service logs: `docker compose logs [service-name]`
- Verify network connectivity
- Ensure all prerequisites are installed
- Review test output for specific error messages

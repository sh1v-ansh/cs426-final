#!/bin/bash
# Port conflict diagnostic script

echo "Checking for port conflicts..."
echo "================================"
echo ""

PORTS=(5432 5433 5434 6379 5672 15672 80)
NAMES=("postgres-courses" "postgres-students" "postgres-enrollments" "redis" "rabbitmq" "rabbitmq-mgmt" "nginx")

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${NAMES[$i]}

    echo -n "Port $PORT ($NAME): "

    # Try to find what's using the port
    if command -v lsof &> /dev/null; then
        RESULT=$(lsof -i :$PORT 2>/dev/null | grep LISTEN)
        if [ -n "$RESULT" ]; then
            echo "IN USE"
            echo "  $RESULT"
        else
            echo "Available"
        fi
    elif command -v netstat &> /dev/null; then
        RESULT=$(netstat -tuln | grep ":$PORT ")
        if [ -n "$RESULT" ]; then
            echo "IN USE"
            echo "  $RESULT"
        else
            echo "Available"
        fi
    elif command -v ss &> /dev/null; then
        RESULT=$(ss -tuln | grep ":$PORT ")
        if [ -n "$RESULT" ]; then
            echo "IN USE"
            echo "  $RESULT"
        else
            echo "Available"
        fi
    else
        echo "Cannot check (no diagnostic tools available)"
    fi
done

echo ""
echo "Checking for running Docker containers..."
echo "=========================================="
docker ps -a --filter "name=cs426" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not running or no containers found"

echo ""
echo "Solutions:"
echo "=========="
echo "1. Stop old containers: docker compose down -v"
echo "2. Find process on port: lsof -i :5433 (then kill -9 <PID>)"
echo "3. Use alternative ports: see docker-compose.alt-ports.yml"

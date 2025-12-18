#!/bin/bash
# Diagnostic script to check if new enrollment code is running

echo "=================================================="
echo "ENROLLMENT SERVICE DIAGNOSTIC"
echo "=================================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check running containers
echo "Running containers:"
echo "==================="
docker ps --filter "name=enrollment" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

# Check enrollment service logs for debug output
echo "Checking enrollment service logs for debug output..."
echo "====================================================="
echo ""

# Get recent logs
LOGS=$(docker compose logs enrollment --tail=50 2>/dev/null)

if echo "$LOGS" | grep -q "\[DEBUG\]"; then
    echo "✓ NEW CODE IS RUNNING - Debug logs found:"
    echo ""
    echo "$LOGS" | grep "\[DEBUG\]" | tail -10
else
    echo "❌ OLD CODE IS RUNNING - No debug logs found!"
    echo ""
    echo "Recent logs:"
    echo "$LOGS" | tail -20
    echo ""
    echo "ACTION REQUIRED:"
    echo "================"
    echo "You need to rebuild the Docker images!"
    echo ""
    echo "Run these commands:"
    echo "  docker compose down -v"
    echo "  docker compose build --no-cache enrollment"
    echo "  docker compose up -d"
fi

echo ""
echo "=================================================="

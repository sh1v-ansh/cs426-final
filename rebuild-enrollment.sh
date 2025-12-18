#!/bin/bash
# Script to rebuild just the enrollment service with new code

echo "=================================================="
echo "REBUILDING ENROLLMENT SERVICE"
echo "=================================================="
echo ""

echo "Step 1: Stopping enrollment service..."
docker compose stop enrollment

echo ""
echo "Step 2: Removing old enrollment container..."
docker compose rm -f enrollment

echo ""
echo "Step 3: Rebuilding enrollment service (no cache)..."
docker compose build --no-cache enrollment

echo ""
echo "Step 4: Starting enrollment service..."
docker compose up -d enrollment

echo ""
echo "Step 5: Waiting for service to be healthy..."
sleep 5

echo ""
echo "Step 6: Checking service status..."
docker compose ps enrollment

echo ""
echo "Step 7: Checking for debug logs..."
sleep 2
docker compose logs enrollment --tail=20 | grep -E "(DEBUG|Starting|Uvicorn)" || echo "No debug output yet"

echo ""
echo "=================================================="
echo "Rebuild complete!"
echo "=================================================="
echo ""
echo "Now run: python3 tests/load_test.py"
echo ""

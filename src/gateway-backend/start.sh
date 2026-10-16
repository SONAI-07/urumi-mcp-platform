#!/bin/bash
set -e

echo "Starting Gateway MCP Server..."
python gateway_server.py &
MCP_PID=$!

echo "Starting Gateway REST API..."
uvicorn api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# If either process dies, kill the other so K8s restarts the whole pod
trap "kill $MCP_PID $API_PID 2>/dev/null" EXIT
wait -n $MCP_PID $API_PID
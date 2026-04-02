#!/bin/bash
# Trading Journal - Start both backend and frontend

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Trading Journal ==="
echo ""

# Backend
echo "[1/2] Starting backend (FastAPI on :8100)..."
cd "$DIR/backend"
if [ ! -d "venv" ]; then
  echo "  Creating Python venv..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi
uvicorn main:app --host 0.0.0.0 --port 8111 --reload &
BACKEND_PID=$!

# Frontend
echo "[2/2] Starting frontend (Vite on :5173)..."
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
  echo "  Installing npm dependencies..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8111"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

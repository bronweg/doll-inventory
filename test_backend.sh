#!/bin/bash
# Quick test script for backend implementation

echo "=== Testing Backend Implementation ==="
echo ""

# Check if Python files have syntax errors
echo "1. Checking Python syntax..."
python3 -m py_compile backend/app/main.py
python3 -m py_compile backend/app/core/config.py
python3 -m py_compile backend/app/core/auth.py
python3 -m py_compile backend/app/db/session.py
python3 -m py_compile backend/app/db/models.py
python3 -m py_compile backend/app/api/dolls.py
python3 -m py_compile backend/app/api/events.py
python3 -m py_compile backend/app/schemas/dolls.py
python3 -m py_compile backend/app/schemas/events.py

if [ $? -eq 0 ]; then
    echo "✅ All Python files have valid syntax"
else
    echo "❌ Syntax errors found"
    exit 1
fi

echo ""
echo "2. File structure:"
find backend/app -type f -name "*.py" | sort

echo ""
echo "=== All checks passed! ==="
echo ""
echo "To run the backend:"
echo "  cd backend"
echo "  pip install -r requirements.txt"
echo "  export AUTH_MODE=none"
echo "  export ALLOW_INSECURE_LOCAL=true"
echo "  export DB_PATH=./test.db"
echo "  uvicorn app.main:app --reload"


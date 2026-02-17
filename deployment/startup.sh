#!/bin/bash
# startup.sh - Railway startup script
# Supports both BOT and WEB panel via SERVICE_TYPE env var

echo "📁 Working directory: $(pwd)"
echo "🐍 Python version: $(python --version)"

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# ── WEB PANEL MODE ──
if [ "$SERVICE_TYPE" = "web" ]; then
    echo "🌐 Starting Web Admin Panel..."
    exec gunicorn web.app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120
fi

# ── BOT MODE (default) ──
echo "🚀 Starting Evgenich Bot on Railway..."

# Run PostgreSQL fixes if needed
echo "🔧 Running PostgreSQL migrations..."
python core/fix_postgresql_columns.py

# Check if migration succeeded
if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL migrations completed successfully"
else
    echo "⚠️ PostgreSQL migrations failed, continuing anyway..."
fi

# Start the main bot
echo "🤖 Starting main bot..."
python main.py

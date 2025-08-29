#!/bin/bash
# startup.sh - Railway startup script

echo "🚀 Starting Evgenich Bot on Railway..."
echo "📁 Working directory: $(pwd)"
echo "🐍 Python version: $(python --version)"

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

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

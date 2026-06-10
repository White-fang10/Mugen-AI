#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# MUGEN AI — Render / Docker Startup Script
# Runs both the Telegram Bot (background) and the Admin Panel (foreground)
# ─────────────────────────────────────────────────────────────────────────────

echo "Starting Mugen AI Telegram Bot..."
# Run the bot in the background
python -m bot.main &

echo "Starting Mugen AI Admin Panel..."
# Use the PORT provided by Render, or default to 8080
PORT="${PORT:-8080}"

# Run uvicorn in the foreground so the container stays alive and binds to the port
exec uvicorn admin_panel.api:app --host 0.0.0.0 --port $PORT

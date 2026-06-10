#!/bin/bash
# MUGEN AI — SD-05 Bot Startup

echo "Starting dummy server for Render port binding..."
python dummy_server.py &

echo "Starting MUGEN AI Telegram Bot..."
python -m bot.main

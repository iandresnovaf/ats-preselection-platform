#!/bin/bash
cd /home/andres/.openclaw/workspace/ats-platform/backend
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

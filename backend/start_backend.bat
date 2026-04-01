@echo off
cd /d "C:\Users\10500\Desktop\plant-app\backend"
start /B "" "C:\Users\10500\Desktop\plant-app\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
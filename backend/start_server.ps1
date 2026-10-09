$env:PYTHONPATH = "C:\Users\hp\FraudLens\backend"
& "C:\Users\hp\FraudLens\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

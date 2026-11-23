$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "backend")
& (Join-Path $Root ".venv\Scripts\python.exe") -m app.db.migrate
& (Join-Path $Root ".venv\Scripts\uvicorn.exe") app.main:app --host 127.0.0.1 --port 8000 --reload

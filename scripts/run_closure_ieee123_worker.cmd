@echo off
REM Closure brief Part E2: one detached node_123 voltage worker (resumable).
REM Usage: scripts\run_closure_ieee123_worker.cmd <worker_index> <n_workers>
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase3_infra_replicability\results\closure_shards"
if not exist "%OUT%" mkdir "%OUT%"
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\closure_ieee123_voltage.py --worker %1 --n-workers %2 >> "%OUT%\ieee123_worker_%1.log" 2>&1

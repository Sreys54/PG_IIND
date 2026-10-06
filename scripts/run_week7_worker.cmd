@echo off
REM Week 7 Step 2: one detached grid worker (resumable: rerun the same command after an interruption).
REM Usage: scripts\run_week7_worker.cmd <worker_index> <n_workers> <n_seeds>
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase3_infra_replicability\results\shards"
if not exist "%OUT%" mkdir "%OUT%"
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\run_week7_grid.py --worker %1 --n-workers %2 --seeds %3 >> "%OUT%\worker_%1.log" 2>&1

@echo off
REM Final capacity (dwell) brief, Parts B-C: one detached worker (resumable: rerun the same command after an interruption).
REM Usage: scripts\run_dwell_worker.cmd <worker_index> <n_workers> [plan_json]
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase3_infra_replicability\results\dwell_shards"
set "PLAN=%3"
if "%PLAN%"=="" set "PLAN=experiments\phase3_infra_replicability\configs\dwell\plans\dwell_main.json"
if not exist "%OUT%" mkdir "%OUT%"
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\run_dwell_capacity.py --worker %1 --n-workers %2 --plan "%PLAN%" >> "%OUT%\worker_%1.log" 2>&1

@echo off
REM Last run: Part 2 bounds (dwell_bounds.json) then Part 3 node_123 voltage; resumable.
REM Usage: scripts\run_last_worker.cmd <worker_index> <n_workers>
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase3_infra_replicability\results\dwell_shards"
if not exist "%OUT%" mkdir "%OUT%"
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\run_dwell_capacity.py --worker %1 --n-workers %2 --plan experiments\phase3_infra_replicability\configs\dwell\plans\dwell_bounds.json >> "%OUT%\last_bounds_%1.log" 2>&1
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\dwell_ieee123_voltage.py --worker %1 --n-workers %2 >> "%OUT%\last_voltage_%1.log" 2>&1

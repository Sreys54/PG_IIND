@echo off
REM Closure brief Part C: one detached worker (resumable: rerun the same command after an interruption).
REM Usage: scripts\run_closure_worker.cmd <worker_index> <n_workers> [cd]
REM   "cd" runs only the C2 constant-demand variants (spawn_multiplier scaled by 8/ports).
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase3_infra_replicability\results\closure_shards"
if not exist "%OUT%" mkdir "%OUT%"
if "%3"=="cd" (
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\run_closure_capacity.py --worker %1 --n-workers %2 --c2-ports 10,12 --c2-constant-demand-levels 0.75,1.0 --c2-constant-demand-kw 100,134.2 >> "%OUT%\worker_cd_%1.log" 2>&1
exit /b
)
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" -W ignore scripts\run_closure_capacity.py --worker %1 --n-workers %2 --c1-levels 0.5,0.75,2.0,2.5 --c2-levels 0.75,1.0 --c2-ports 10,12 --c2-kw 100.6,134.2 >> "%OUT%\worker_%1.log" 2>&1

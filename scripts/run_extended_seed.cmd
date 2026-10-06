@echo off
REM Week 6 Part 0: run one extended-training seed, detached-friendly.
REM Usage: scripts\run_extended_seed.cmd <train_seed> <deadline ISO-8601 with offset> [--resume]
REM stdout/stderr go to the seed's (gitignored) model directory.
cd /d "%~dp0.."
set "PYTHONPATH=."
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"
set "OUT=experiments\phase2_algorithms\models\TD3_vanilla_extended_ts%1"
if not exist "%OUT%" mkdir "%OUT%"
"C:\Users\Santi\AppData\Local\Programs\Python\Python311\python.exe" scripts\train_td3_extended.py --seed %1 --reward vanilla --deadline %2 --price-cache --torch-threads 1 %3 >> "%OUT%\stdout.log" 2>> "%OUT%\stderr.log"

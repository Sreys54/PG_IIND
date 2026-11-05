#!/bin/bash
# Week 8 C3 long-budget sensitivity, slot B: seed 101 (slot B then runs the tests).
cd "$(dirname "$0")/../../.."
export PYTHONPATH=.
python scripts/train_td3_safe.py --seed 101 --deadline 2026-11-05T23:59:00-05:00 --price-cache --torch-threads 1 \
  --state service_causal --fixed-budget --max-steps 2000000 --output-root C:/ev2gym_runs/w8_td3_safe_long \
  > C:/ev2gym_runs/w8_td3_safe_long_ts101.log 2>&1
echo "seed 101 exit $?"
